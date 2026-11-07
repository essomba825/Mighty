"""Import exam PDFs, generate bilingual corrections with Gemini, and publish for pilot.

The command is resumable: each successful paper is exported to exams/generated/
and stored in Django before the next PDF starts.
"""
import base64
import hashlib
import io
import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from education.models import Subject
from exams.models import (ExamPaper, ExamQuestion, MarkCriterion, PaperCorrection,
                          QuestionCorrection)


DEFAULT_ROOT = Path(r'C:\Users\Petty Cash sas\Downloads\Mega Mighty Sixers - Ressources GCE')
MODEL_DEFAULT = 'gemini-2.5-flash'
OUTPUT_DIR = Path(settings.BASE_DIR) / 'exams' / 'generated'
MAX_INLINE_PDF_BYTES = 18 * 1024 * 1024

SUBJECT_ALIASES = {
    'biology': ('biology', 'biologie'),
    'human biology': ('human biology', 'human-biologie'),
    'chemistry': ('chemistry', 'chimie'),
    'mathematics': ('mathematics', 'mathematiques', 'maths'),
    'physics': ('physics', 'physique'),
}
SUBJECT_CODES = {
    ('al', 'biology', ''): '0710',
    ('al', 'chemistry', ''): '0715',
    ('al', 'physics', ''): '0780',
    ('al', 'mathematics', 'mechanics'): '0765',
    ('al', 'mathematics', 'statistics'): '0770',
    ('ol', 'biology', ''): '0510',
    ('ol', 'human biology', ''): '0565',
    ('ol', 'chemistry', ''): '0515',
    ('ol', 'mathematics', ''): '0570',
    ('ol', 'physics', ''): '0580',
}

SYSTEM_PROMPT = """Read the supplied Cameroon GCE exam page and solve every question/sub-question on it. Never guess unreadable data; flag it. Do not invent marks. Mark every model-made rubric proposed_by_model. Return compact JSON only, with exactly this structure: {"paper":{"total_marks":null,"duration_minutes":null},"questions":[{"number":"Q1(a)","parent_number":"Q1","order":1,"kind":"short","statement_en":"question text","choices":[],"source_pages":[2],"marks":1,"answer":{"final":"answer","option_label":"","option_text":""},"explanation_en":"one concise sentence","explanation_fr":"une phrase concise","rubric_source":"proposed_by_model","criteria":[{"key":"answer","kind":"answer","marks":1,"description_en":"credit point","description_fr":"point de correction"}],"review_flags":[]}]} Keep statement and explanations short; no repeated wording or chain-of-thought. MCQ: return the correct option label and its text. Use one criterion for MCQ and at most two for other questions."""


def _fold(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(c for c in value if not unicodedata.combining(c)).lower()


def _metadata(path, root):
    name = path.stem
    folded = _fold(name)
    parts = [_fold(part) for part in path.relative_to(root).parts]
    all_text = ' '.join(parts + [folded])
    folder_level = 'ol' if any('o-level' in part or part == 'ol' for part in parts) else 'al'
    explicit_ol = bool(re.search(r'(^|[^a-z])(?:ol|o-level)(?:[^a-z]|$)|gce_ol|human.?biology', folded))
    level = 'ol' if explicit_ol else folder_level

    if 'human biology' in all_text or 'human-biologie' in all_text:
        subject = 'human biology'
    else:
        subject = next((key for key, aliases in SUBJECT_ALIASES.items()
                        if key != 'human biology' and any(alias in all_text for alias in aliases)), None)
    if subject is None:
        return None
    if re.search(r'(?:19|20)\d{2}\s*[-Ã¢â‚¬â€œ]\s*(?:19|20)\d{2}', name):
        return None  # A compiled booklet is not one exam session.

    route = ''
    if subject == 'mathematics':
        if 'mechanic' in folded:
            route = 'mechanics'
        elif 'statistic' in folded:
            route = 'statistics'

    year_match = re.search(r'(?:19|20)\d{2}', name)
    year = int(year_match.group(0)) if year_match else None
    paper_match = (re.search(r'(?:paper|p)[-_ ]?([1-3])(?:\D|$)', folded)
                   or re.search(r'-(?:copy-)?([1-3])(?:-copy)?$', folded))
    paper_number = int(paper_match.group(1)) if paper_match else 1
    is_mock = 'mock' in folded or 'regional' in folded
    session = 'mock' if is_mock else 'june'
    code = SUBJECT_CODES.get((level, subject, route), SUBJECT_CODES.get((level, subject, ''), ''))
    level_name = 'O/L' if level == 'ol' else 'A/L'
    route_label = f' with {route}' if route else ''
    title = f'Cameroon GCE {level_name} {year or "Unknown year"} {subject.title()}{route_label} Paper {paper_number}'
    if is_mock:
        title += ' Mock'
    return {
        'level': level, 'subject': subject, 'route': route, 'year': year,
        'paper_number': paper_number, 'session': session,
        'paper_type': 'mock' if is_mock else 'official', 'subject_code': code,
        'title': title, 'source_name': path.name,
    }


def _pdf_inventory(root):
    """Hash first, then keep one source path per exact PDF, preferring clear filenames."""
    found = {}
    for path in sorted(root.rglob('*.pdf')):
        meta = _metadata(path, root)
        if not meta or not meta['year']:
            continue
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        sha = digest.hexdigest()
        explicit = bool(re.search(r'(^|[^a-z])(?:ol|o-level|al|a-level)(?:[^a-z]|$)', _fold(path.name)))
        score = (2 if explicit else 0) + (1 if path.stat().st_size > 10_000 else 0)
        if sha not in found or score > found[sha][2]:
            found[sha] = (path, meta, score, sha)
    return [value[:2] + (value[3],) for value in found.values()]


def _subject_for(meta):
    aliases = SUBJECT_ALIASES[meta['subject']]
    subjects = Subject.objects.filter(level=meta['level'])
    for subject in subjects:
        candidate = _fold(f'{subject.name} {subject.slug}')
        if any(alias in candidate for alias in aliases):
            return subject
    if meta['subject'] == 'human biology':
        return Subject.objects.create(
            name='Human Biology', slug=f'human-biology-{meta["level"]}',
            level=meta['level'], description='Cameroon GCE Human Biology past papers',
            icon='mdi-human', color='#3b82f6')
    raise CommandError(f'No Django Subject matches {meta["subject"]} ({meta["level"]}).')


def _call_gemini_chunk(pdf_bytes, meta, model, api_key, page_range, debug_key,
                       page_text=''):
    size = len(pdf_bytes)
    if size > MAX_INLINE_PDF_BYTES:
        raise ValueError(f'PDF exceeds inline limit ({size} bytes); use Gemini Files API.')
    user_prompt = (
        f"Paper metadata from filename: {json.dumps(meta, ensure_ascii=False)}. "
        f'Attached pages from the complete paper: {page_range}. '
        f'In source_pages, use original PDF page numbers from {page_range} (1-based), not positions within this attachment. '
        'Extract and correct every question visible on these pages only. '
        'Return a compact JSON answer. Explanations are one sentence per language; for MCQ give only the correct option label and option text. Do not repeat question text.'
    )
    payload = {
        'contents': [{'parts': [
            {'text': SYSTEM_PROMPT + '\n\n' + user_prompt + (
                '\n\nExtracted PDF text (preserve question numbering and symbols):\n' + page_text
                if len(page_text.strip()) >= 300 else '')},
            *([] if len(page_text.strip()) >= 300 else [{
                'inline_data': {
                    'mime_type': 'application/pdf',
                    'data': base64.b64encode(pdf_bytes).decode('ascii'),
                }
            }]),
        ]}],
        'generationConfig': {
            'temperature': 0.1,
            'responseMimeType': 'application/json',
            # Gemini 2.5 Flash otherwise spends part of this hard cap thinking,
            # which can truncate structured JSON before its closing braces.
            'thinkingConfig': {'thinkingBudget': 0},
            'maxOutputTokens': 8192,
            'responseSchema': {
                'type': 'OBJECT',
                'properties': {
                    'paper': {'type': 'OBJECT', 'properties': {
                        'total_marks': {'type': 'NUMBER', 'nullable': True},
                        'duration_minutes': {'type': 'INTEGER', 'nullable': True},
                    }},
                    'questions': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
                        'number': {'type': 'STRING'}, 'parent_number': {'type': 'STRING', 'nullable': True},
                        'order': {'type': 'INTEGER'}, 'kind': {'type': 'STRING'},
                        'statement_en': {'type': 'STRING'},
                        'choices': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
                            'label': {'type': 'STRING'}, 'text': {'type': 'STRING'},
                        }}},
                        'source_pages': {'type': 'ARRAY', 'items': {'type': 'INTEGER'}},
                        'marks': {'type': 'NUMBER', 'nullable': True},
                        'answer': {'type': 'OBJECT', 'properties': {
                            'final': {'type': 'STRING'}, 'option_label': {'type': 'STRING'},
                            'option_text': {'type': 'STRING'},
                        }},
                        'explanation_en': {'type': 'STRING'}, 'explanation_fr': {'type': 'STRING'},
                        'rubric_source': {'type': 'STRING'},
                        'criteria': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
                            'key': {'type': 'STRING'}, 'kind': {'type': 'STRING'},
                            'marks': {'type': 'NUMBER'}, 'description_en': {'type': 'STRING'},
                            'description_fr': {'type': 'STRING'},
                        }}},
                        'review_flags': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
                    }}},
                },
                'required': ['paper', 'questions'],
            },
        },
    }
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?'
    url = endpoint + urlencode({'key': api_key})
    request = Request(url, data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    for attempt in range(5):
        try:
            with urlopen(request, timeout=90) as response:
                response_data = json.loads(response.read().decode('utf-8'))
            candidate = response_data['candidates'][0]
            text = ''.join(part.get('text', '')
                           for part in candidate.get('content', {}).get('parts', []))
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                finish_reason = candidate.get('finishReason', 'unknown')
                raw_path = OUTPUT_DIR / f'{debug_key}.gemini_raw.txt'
                raw_path.write_text(text, encoding='utf-8')
                try:
                    result = _repair_json_with_ollama(text)
                except ValueError as exc:
                    raise ValueError(f'{exc} (Gemini finishReason={finish_reason}, chars={len(text)}).') from None
            if not isinstance(result.get('questions'), list):
                raise ValueError('Gemini returned no questions array.')
            return result
        except HTTPError as exc:
            if exc.code == 429:
                raise RuntimeError(
                    'Gemini HTTP 429: quota or rate limit reached; retry after quota reset.') from None
            if exc.code in (500, 502, 503, 504) and attempt < 4:
                time.sleep(min(60, 8 * (attempt + 1)))
                continue
            raise RuntimeError(f'Gemini HTTP {exc.code}; response body withheld.') from None
        except URLError as exc:
            if attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f'Gemini network error: {exc.reason}') from None
    raise RuntimeError('Gemini retries exhausted.')


def _call_gemini(path, meta, model, api_key):
    """Split PDFs into one-page calls and checkpoint each successful chunk."""
    from pypdf import PdfReader, PdfWriter

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    reader = PdfReader(str(path))
    chunk_dir = OUTPUT_DIR / f'{digest}.chunks'
    chunk_dir.mkdir(parents=True, exist_ok=True)
    page_count = len(reader.pages)
    full_result = {'paper': {}, 'questions': []}
    seen = {}

    def pages_pdf(first, last):
        writer = PdfWriter()
        for page_index in range(first, last):
            writer.add_page(reader.pages[page_index])
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    def process_range(first, last):
        key = f'pages-{first + 1:03d}-{last:03d}'
        cache = chunk_dir / f'{key}.json'
        if cache.exists():
            return json.loads(cache.read_text(encoding='utf-8'))
        page_label = f'{first + 1}-{last}'
        try:
            text = '\n'.join((reader.pages[index].extract_text() or '')
                             for index in range(first, last)).strip()
            result = _call_gemini_chunk(
                pages_pdf(first, last), meta, model, api_key, page_label,
                f'{digest}.{key}', page_text=text if len(text) >= 300 else '')
        except ValueError as exc:
            if last - first <= 1:
                raise
            midpoint = first + (last - first) // 2
            left = process_range(first, midpoint)
            right = process_range(midpoint, last)
            combined = {
                'paper': left.get('paper') or right.get('paper') or {},
                'questions': (left.get('questions') or []) + (right.get('questions') or []),
                'split_reason': str(exc)[:300],
            }
            return combined
        result['_page_offset'] = first
        for item in result.get('questions') or []:
            item['_source_page_offset'] = first
        cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result

    # One-page chunks keep vision input and structured output bounded.
    for first in range(0, page_count):
        last = first + 1
        result = process_range(first, last)
        if not full_result['paper']:
            full_result['paper'] = result.get('paper') or {}
        for local_index, item in enumerate(result.get('questions') or [], 1):
            question = dict(item)
            offset = question.pop('_source_page_offset', result.get('_page_offset', first))
            raw_pages = question.get('source_pages')
            if isinstance(raw_pages, list):
                question['source_pages'] = [
                    int(page) for page in raw_pages
                    if str(page).isdigit()
                ]
            else:
                question['source_pages'] = list(range(first + 1, last + 1))
            question['_source_order'] = offset * 1000 + int(question.get('order') or local_index)
            number = str(question.get('number') or f'Q{len(seen) + 1}')
            previous = seen.get(number)
            if previous is None or len(str(question.get('statement_en') or '')) > len(str(previous.get('statement_en') or '')):
                seen[number] = question
            elif previous is not None:
                previous['source_pages'] = sorted(set(previous.get('source_pages', []) + question.get('source_pages', [])))

    full_result['questions'] = sorted(seen.values(), key=lambda q: q.get('_source_order', 0))
    if not full_result['questions']:
        raise ValueError('No question text was extracted from any page of this PDF.')
    for index, question in enumerate(full_result['questions'], 1):
        question['order'] = index
        question.pop('_source_order', None)
    full_result['source_pages_total'] = page_count
    return full_result


def _repair_json_with_ollama(broken):
    """Use local qwen only to repair JSON syntax; it must preserve all values."""
    payload = {
        'model': 'qwen3:4b', 'stream': False, 'format': 'json',
        'messages': [
            {'role': 'system', 'content': (
                'Repair the syntax of this JSON document only. Preserve all fields and values exactly. '
                'Do not solve, rewrite, translate, summarize, or add content. Return the repaired JSON object only.')},
            {'role': 'user', 'content': broken},
        ],
        'options': {'temperature': 0},
    }
    request = Request('http://localhost:11434/api/chat',
                      data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
        content = result['message']['content']
        repaired = json.loads(content)
        if isinstance(repaired.get('questions'), list) and repaired['questions']:
            return repaired
    except Exception:
        pass
    raise ValueError('Gemini returned malformed JSON and local qwen repair did not recover it.')


def _confidence(value):
    try:
        return max(0, min(1, float(value)))
    except (TypeError, ValueError):
        return None


def _marks(value):
    try:
        return round(float(value), 2) if value is not None else None
    except (TypeError, ValueError):
        return None


def _import_correction(paper, data, model):
    generated = data.get('paper') or {}
    questions = data.get('questions') or []
    PaperCorrection.objects.filter(paper=paper, status=PaperCorrection.Status.PUBLISHED).update(
        status=PaperCorrection.Status.ARCHIVED)
    version_no = (paper.correction_versions.order_by('-version')
                  .values_list('version', flat=True).first() or 0) + 1
    question_map = {}
    with transaction.atomic():
        version = PaperCorrection.objects.create(
            paper=paper, version=version_no, status=PaperCorrection.Status.PUBLISHED,
            generated_by='Gemini API', generation_model=model, is_machine_generated=True,
            generation_metadata={
                'paper_identity_confidence': _confidence(generated.get('identity_confidence')),
                'paper_review_flags': generated.get('review_flags') or [],
                'rubric_sources': sorted({q.get('rubric_source', 'unknown') for q in questions}),
                'question_count_returned': len(questions),
                'imported_at': timezone.now().isoformat(),
            })
        paper.total_marks = _marks(generated.get('total_marks'))
        duration = generated.get('duration_minutes')
        paper.duration_minutes = int(duration) if str(duration or '').isdigit() else None
        paper.save(update_fields=['total_marks', 'duration_minutes'])
        for index, item in enumerate(questions, 1):
            number = str(item.get('number') or f'Q{index}')[:24]
            flags = item.get('review_flags') if isinstance(item.get('review_flags'), list) else []
            confidence = _confidence(item.get('extraction_confidence'))
            question, _ = ExamQuestion.objects.update_or_create(
                paper=paper, number=number,
                defaults={
                    'parent': question_map.get(str(item.get('parent_number') or '')),
                    'order': int(item.get('order') or index),
                    'kind': item.get('kind') if item.get('kind') in ExamQuestion.Kind.values else ExamQuestion.Kind.UNKNOWN,
                    'statement': str(item.get('statement_en') or '[Question text not extracted]'),
                    'statement_fr': str(item.get('statement_fr') or ''),
                    'raw_ocr': str(item.get('raw_ocr') or ''),
                    'choices': item.get('choices') if isinstance(item.get('choices'), list) else [],
                    'source_pages': item.get('source_pages') if isinstance(item.get('source_pages'), list) else [],
                    'marks': _marks(item.get('marks')),
                    'extraction_confidence': confidence,
                    'needs_human_review': True,
                    'review_flags': flags,
                })
            question_map[number] = question
        for index, item in enumerate(questions, 1):
            number = str(item.get('number') or f'Q{index}')[:24]
            question = question_map[number]
            flags = item.get('review_flags') if isinstance(item.get('review_flags'), list) else []
            confidence = _confidence(item.get('confidence', item.get('extraction_confidence')))
            answer = item.get('answer') if isinstance(item.get('answer'), dict) else {'final': item.get('answer', '')}
            correction = QuestionCorrection.objects.create(
                version=version, question=question, answer=answer,
                explanation_en=str(item.get('explanation_en') or ''),
                explanation_fr=str(item.get('explanation_fr') or ''),
                solution_steps=item.get('solution_steps') if isinstance(item.get('solution_steps'), list) else [],
                confidence=confidence,
                needs_human_review=True,
                review_flags=flags,
                source_notes=f"Rubric provenance: {item.get('rubric_source', 'unknown')}",
            )
            for criterion_index, criterion in enumerate(item.get('criteria') or [], 1):
                points = _marks(criterion.get('marks'))
                if points is None or points < 0:
                    continue
                kind = criterion.get('kind') or criterion.get('criterion_type') or 'other'
                if kind not in MarkCriterion.CriterionType.values:
                    kind = MarkCriterion.CriterionType.OTHER
                MarkCriterion.objects.create(
                    correction=correction, order=criterion_index,
                    key=str(criterion.get('key') or '')[:60], criterion_type=kind,
                    description_en=str(criterion.get('description_en') or 'Award for this criterion.'),
                    description_fr=str(criterion.get('description_fr') or ''), marks=points,
                    accepted_answers=criterion.get('accepted_answers') if isinstance(criterion.get('accepted_answers'), list) else [],
                    follow_through=bool(criterion.get('follow_through')),
                    depends_on=str(criterion.get('depends_on') or '')[:60],
                )
    return version, len(questions)


class Command(BaseCommand):
    help = 'Import GCE paper PDFs and generate bilingual, pilot-published corrections with Gemini.'

    def add_arguments(self, parser):
        parser.add_argument('--source-root', default=str(DEFAULT_ROOT))
        parser.add_argument('--model', default=MODEL_DEFAULT)
        parser.add_argument('--subject', choices=['biology', 'human biology', 'chemistry', 'mathematics', 'physics'])
        parser.add_argument('--level', choices=['ol', 'al'])
        parser.add_argument('--limit', type=int)
        parser.add_argument('--filename', help='Process only the PDF whose filename contains this text.')
        parser.add_argument('--force-new-version', action='store_true')
        parser.add_argument('--no-pdf-copy', action='store_true',
                            help='Do not copy source PDFs into Django MEDIA_ROOT.')
        parser.add_argument('--delay', type=float, default=6.5,
                            help='Seconds between Gemini calls to stay under common free-tier limits.')

    def handle(self, *args, **options):
        root = Path(options['source_root']).expanduser()
        if not root.is_dir():
            raise CommandError(f'Source directory does not exist: {root}')
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            raise CommandError('Set GEMINI_API_KEY in the process environment; the key is never saved in Django settings.')

        inventory = _pdf_inventory(root)
        subject_filter = _fold(options['subject']) if options.get('subject') else None
        selected = []
        for path, meta, sha in inventory:
            if options.get('filename') and options['filename'].casefold() not in path.name.casefold():
                continue
            if options.get('level') and meta['level'] != options['level']:
                continue
            if subject_filter and _fold(meta['subject']) != subject_filter:
                continue
            selected.append((path, meta, sha))
        if options.get('limit'):
            selected = selected[:options['limit']]
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f'{len(inventory)} distinct PDFs found; {len(selected)} selected.')
        success = skipped = failed = 0

        for index, (path, meta, sha) in enumerate(selected, 1):
            json_path = OUTPUT_DIR / f'{sha}.json'
            try:
                subject = _subject_for(meta)
                paper, created = ExamPaper.objects.get_or_create(
                    source_sha256=sha,
                    defaults={
                        'subject': subject, 'subject_code': meta['subject_code'],
                        'route': meta['route'], 'year': meta['year'],
                        'session': meta['session'], 'paper_number': meta['paper_number'],
                        'paper_type': meta['paper_type'], 'title': meta['title'],
                        'source_name': meta['source_name'],
                    })
                if not options['no_pdf_copy'] and not paper.source_pdf:
                    clean_name = re.sub(r'[^A-Za-z0-9._-]+', '_', path.name)
                    with path.open('rb') as source:
                        paper.source_pdf.save(f'{sha[:12]}-{clean_name}', File(source), save=True)
                if (paper.correction_versions.filter(status=PaperCorrection.Status.PUBLISHED).exists()
                        and not options['force_new_version']):
                    skipped += 1
                    self.stdout.write(f'[{index}/{len(selected)}] already published: {paper.title}')
                    continue
                if json_path.is_file() and not options['force_new_version']:
                    data = json.loads(json_path.read_text(encoding='utf-8'))
                else:
                    self.stdout.write(f'[{index}/{len(selected)}] Gemini reading: {path.name}')
                    data = _call_gemini(path, meta, options['model'], api_key)
                    data['source'] = {
                        'filename': path.name, 'sha256': sha,
                        'source_root_category': path.parent.parent.name,
                        'generated_at': timezone.now().isoformat(),
                        'model': options['model'],
                    }
                    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                version, q_count = _import_correction(paper, data, options['model'])
                success += 1
                self.stdout.write(self.style.SUCCESS(
                    f'[{index}/{len(selected)}] published v{version.version}: {paper.title} Ã¢â‚¬â€ {q_count} questions'))
                if index < len(selected) and not json_path.is_file():
                    time.sleep(options['delay'])
                elif index < len(selected):
                    time.sleep(options['delay'])
            except Exception as exc:
                failed += 1
                # Never print request URLs or credentials; the key is in the query string.
                self.stderr.write(self.style.ERROR(
                    f'[{index}/{len(selected)}] FAILED {path.name}: {type(exc).__name__}: {exc}'))

        self.stdout.write(self.style.SUCCESS(
            f'Complete: {success} generated/published, {skipped} already available, {failed} failed.'))
