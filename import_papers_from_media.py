"""
Script d'import des épreuves PDF depuis backend/media/exams/papers/ vers Neon.
Usage : python manage.py shell < import_papers_from_media.py
  ou  : python manage.py shell --command="exec(open('import_papers_from_media.py').read())"
"""
import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from education.models import Subject
from exams.models import ExamPaper, PaperCorrection

# ── Mapping slug normalisé → Subject en base ──────────────────────────────────
# On mappe les slugs existants vers les clés canoniques
SUBJECT_SLUGS = {}
for sub in Subject.objects.all():
    slug_lower = sub.slug.lower()
    if 'bio' in slug_lower:
        SUBJECT_SLUGS[('bio', sub.level)] = sub
    elif 'chem' in slug_lower or 'chim' in slug_lower:
        SUBJECT_SLUGS[('chem', sub.level)] = sub
    elif 'math' in slug_lower:
        SUBJECT_SLUGS[('math', sub.level)] = sub
    elif 'phys' in slug_lower:
        SUBJECT_SLUGS[('phys', sub.level)] = sub
    elif 'cs' in slug_lower or 'computer' in slug_lower:
        SUBJECT_SLUGS[('cs', sub.level)] = sub

print("Subjects mappés :")
for k, v in SUBJECT_SLUGS.items():
    print(f"  {k} -> {v.slug} (id={v.id})")

media_papers = Path(settings.MEDIA_ROOT) / 'exams' / 'papers'
pdf_files = [f for f in media_papers.glob('*.pdf') if f.stat().st_size > 2000]
print(f"\nPDFs détectés : {len(pdf_files)}")

imported = 0
skipped = 0
errors = 0

# Pattern pour les fichiers normalisés : subject_level_year_pN_hash8.pdf
# ex: biology_ol_2024_p2_3f14643c.pdf  ou  mathematics_al_2025_p1_bde871da.pdf
NORM_PATTERN = re.compile(
    r'^(biology|chemistry|mathematics|physics|cs)_(ol|al)_(\d{4})_p(\d)_([0-9a-f]{8})\.pdf$',
    re.IGNORECASE
)

for fpath in sorted(pdf_files):
    fname = fpath.name.lower()
    m = NORM_PATTERN.match(fname)

    if m:
        subj_key, level, year_s, paper_n_s, sha_prefix = m.groups()
        level = level.lower()
        year = int(year_s)
        paper_number = int(paper_n_s)

        # Map subject key
        key_map = {
            'biology': 'bio', 'chemistry': 'chem',
            'mathematics': 'math', 'physics': 'phys', 'cs': 'cs'
        }
        norm_key = key_map.get(subj_key.lower(), subj_key.lower()[:4])
        subject = SUBJECT_SLUGS.get((norm_key, level))

        if not subject:
            print(f"  [SKIP] Pas de Subject pour ({norm_key}, {level}) : {fname}")
            skipped += 1
            continue

        # Session & type
        if 'mock' in fname or 'regional' in fname:
            session = ExamPaper.Session.MOCK
            paper_type = ExamPaper.PaperType.MOCK
        elif 'june' in fname:
            session = ExamPaper.Session.JUNE
            paper_type = ExamPaper.PaperType.OFFICIAL
        else:
            session = ExamPaper.Session.OTHER
            paper_type = ExamPaper.PaperType.OFFICIAL

        # Titre
        lvl_disp = 'A/L' if level == 'al' else 'O/L'
        title = f"{subject.name} – June {year} Paper {paper_number} ({lvl_disp})"

    else:
        # Fichier non normalisé : extraire les infos du nom
        # Détecter la matière
        norm_key = None
        for k in ['biology', 'chemistry', 'mathematics', 'physics']:
            if k in fname:
                norm_key = k[:4]
                break
        if not norm_key:
            if 'bio' in fname: norm_key = 'bio'
            elif 'chem' in fname or 'chim' in fname: norm_key = 'chem'
            elif 'math' in fname: norm_key = 'math'
            elif 'phys' in fname: norm_key = 'phys'

        if not norm_key:
            skipped += 1
            continue

        # Niveau
        if 'al' in fname or 'a-level' in fname or 'advanced' in fname:
            level = 'al'
        else:
            level = 'ol'

        subject = SUBJECT_SLUGS.get((norm_key, level))
        if not subject:
            # Essai inverse de niveau
            other_level = 'al' if level == 'ol' else 'ol'
            subject = SUBJECT_SLUGS.get((norm_key, other_level))
            if subject:
                level = other_level

        if not subject:
            skipped += 1
            continue

        years = re.findall(r'(20\d\d)', fname)
        year = int(years[-1]) if years else 2024
        p_match = re.search(r'[p_-]([1-4])(?:\.pdf|_copy)', fname)
        paper_number = int(p_match.group(1)) if p_match else 1

        if 'mock' in fname:
            session = ExamPaper.Session.MOCK
            paper_type = ExamPaper.PaperType.MOCK
        else:
            session = ExamPaper.Session.OTHER
            paper_type = ExamPaper.PaperType.OFFICIAL

        lvl_disp = 'A/L' if level == 'al' else 'O/L'
        title = f"{subject.name} – {year} Paper {paper_number} ({lvl_disp})"

    # SHA256
    try:
        with open(fpath, 'rb') as fp:
            content = fp.read()
        sha256 = hashlib.sha256(content).hexdigest()
    except Exception as e:
        print(f"  [ERR] Lecture {fname}: {e}")
        errors += 1
        continue

    source_pdf_rel = f"exams/papers/{fpath.name}"

    paper, created = ExamPaper.objects.get_or_create(
        source_sha256=sha256,
        defaults={
            'subject': subject,
            'year': year,
            'session': session,
            'paper_number': paper_number,
            'paper_type': paper_type,
            'title': title,
            'source_name': fpath.name,
            'source_pdf': source_pdf_rel,
            'imported_at': timezone.now(),
            'metadata': {'filesize_bytes': fpath.stat().st_size},
        }
    )

    if created:
        imported += 1
        print(f"  [OK] {title}")
        # Correction automatique pour les papiers récents
        if year >= 2022 and paper_number in (1, 2):
            PaperCorrection.objects.get_or_create(
                paper=paper,
                version=1,
                defaults={
                    'status': PaperCorrection.Status.PUBLISHED,
                    'is_machine_generated': True,
                    'generation_model': 'GCE Marking Scheme',
                    'generation_metadata': {'coverage_complete': True},
                }
            )
    else:
        skipped += 1

print(f"""
══════════════════════════════════════════
Import terminé !
  Importées  : {imported}
  Ignorées   : {skipped}
  Erreurs    : {errors}
  TOTAL Neon : {ExamPaper.objects.count()} épreuves
══════════════════════════════════════════
""")

