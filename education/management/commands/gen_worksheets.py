"""Genere une fiche d'exercices bilingue + son corrige pour les lecons qui
n'ont pas encore de PDF de travail, puis les attache comme `Resource`.

Les exercices sont construits a partir des questions deja validees de la lecon
(micro-etapes + quiz) : le contenu reste donc strictement au programme et deja
passe par le controle qualite.

Usage :
    python manage.py gen_worksheets                  # lecons publiees sans PDF
    python manage.py gen_worksheets --lesson 32      # une seule lecon
    python manage.py gen_worksheets --force          # regenere meme si un PDF existe
    python manage.py gen_worksheets --dry-run        # n'ecrit rien
"""
import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from fpdf import FPDF

from education.models import Lesson, Question, Resource

PRIMARY = (16, 30, 60)
ACCENT = (201, 162, 39)

# Correspondance des symboles unicode vers du texte latin-1 sur pour la police
# "helvetica" des PDF (fpdf2 ne gere nativement que latin-1).
_SYMBOLS = {
    '\u00b2': '^2', '\u00b3': '^3', '\u00b9': '^1',
    '\u00d7': 'x', '\u00f7': '/', '\u2248': '~', '\u2260': '!=',
    '\u2264': '<=', '\u2265': '>=', '\u2192': '->', '\u21d2': '=>',
    '\u03b8': 'theta', '\u03c0': 'pi', '\u03b1': 'alpha', '\u03b2': 'beta',
    '\u00b0': ' deg', '\u2212': '-', '\u2013': '-', '\u2014': '-',
    '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
    '\u2026': '...', '\u00a0': ' ', '\u2022': '-', '\u2211': 'sum',
    '\u221a': 'sqrt', '\u221e': 'inf', '\u2261': '=', '\u2208': 'in',
}


def _ascii(text):
    """Normalise une chaine pour les polices coeur de fpdf2 (latin-1)."""
    if text is None:
        return ''
    text = str(text)
    for src, dst in _SYMBOLS.items():
        text = text.replace(src, dst)
    return text.encode('latin-1', 'replace').decode('latin-1')


def _question_to_exercise(question):
    """Retourne (enonce, corrige) pour une question, en texte latin-1."""
    enonce = _ascii(question.text)
    enonce_fr = _ascii(question.text_fr)
    if enonce_fr and enonce_fr != enonce:
        enonce = f'{enonce}\n{enonce_fr}'

    expl = _ascii(question.explanation)
    expl_fr = _ascii(question.explanation_fr)
    lines = []

    if question.kind == Question.Kind.MCQ:
        for choice in question.choices.all():
            label = _ascii(choice.text)
            label_fr = _ascii(choice.text_fr)
            if label_fr and label_fr != label:
                label = f'{label} / {label_fr}'
            mark = ' *' if choice.is_correct else ''
            lines.append(f'   - {label}{mark}')
        correct = next(
            (c for c in question.choices.all() if c.is_correct), None)
        if correct is not None:
            lines.append(f'Answer: {_ascii(correct.text)}')
    elif question.kind in (Question.Kind.NUMERIC, Question.Kind.TEXT):
        accepted = (question.config or {}).get('accepted') or []
        if accepted:
            lines.append('Answer: ' + ', '.join(_ascii(a) for a in accepted))
    elif question.kind == Question.Kind.ORDERED:
        items = (question.config or {}).get('items') or []
        if items:
            lines.append('Answer: ' + ' -> '.join(_ascii(i) for i in items))
    elif question.kind == Question.Kind.PAIRING:
        pairs = (question.config or {}).get('pairs') or []
        if pairs:
            lines.append('Answer: ' + '; '.join(
                f'{_ascii(a)} = {_ascii(b)}' for a, b in pairs))

    if expl or expl_fr:
        if expl:
            lines.append(expl)
        if expl_fr and expl_fr != expl:
            lines.append(expl_fr)
    return enonce, '\n'.join(lines)


def collect_exercises(lesson):
    """Regroupe les questions de la lecon (etapes puis quiz), sans doublon."""
    seen = set()
    exercises = []
    qs = list(
        Question.objects.filter(step__lesson=lesson)
        .select_related('step').prefetch_related('choices')
        .order_by('step__order'))
    qs += list(
        Question.objects.filter(quiz__lesson=lesson)
        .prefetch_related('choices').order_by('order'))
    for q in qs:
        key = _ascii(q.text).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        enonce, corrige = _question_to_exercise(q)
        exercises.append({'enonce': enonce, 'corrige': corrige})
    return exercises


class Command(BaseCommand):
    help = "Genere exercices + corriges PDF et les attache aux lecons"

    def add_arguments(self, parser):
        parser.add_argument('--lesson', type=int, action='append',
                            help='Identifiant de lecon (repetable)')
        parser.add_argument('--force', action='store_true',
                            help='Regenere meme si un PDF est deja attache')
        parser.add_argument('--dry-run', action='store_true',
                            help='Affiche le plan sans rien ecrire')
        parser.add_argument('--min-questions', type=int, default=3,
                            help='Nombre minimal de questions pour generer')

    def handle(self, *args, **options):
        lessons = Lesson.objects.filter(status=Lesson.Status.PUBLISHED)
        if options['lesson']:
            lessons = lessons.filter(pk__in=options['lesson'])
        lessons = lessons.annotate(n_pdf=Count(
            'resources', filter=Q(resources__kind=Resource.Kind.PDF)
        )).order_by('id')
        if not options['force']:
            lessons = lessons.filter(n_pdf=0)

        count = 0
        for lesson in lessons:
            exercises = collect_exercises(lesson)
            if len(exercises) < options['min_questions']:
                self.stdout.write(self.style.WARNING(
                    f'[skip] {lesson.id} {lesson.title} : '
                    f'{len(exercises)} question(s)'))
                continue
            if options['dry_run']:
                self.stdout.write(
                    f'[dry] {lesson.id} {lesson.title} : '
                    f'{len(exercises)} exercice(s)')
                count += 1
                continue
            self._write_lesson(lesson, exercises)
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f'[TERMINE] {count} lecon(s) traitee(s).'))

    def _write_lesson(self, lesson, exercises):
        base = f'lesson{lesson.id}'
        subject = _ascii(lesson.chapter.subject.name)
        level = lesson.chapter.subject.get_level_display()
        ex_txt = self._render(
            f'Practice worksheet - {_ascii(lesson.title)}',
            f'{level} - {subject} - Fiche d\'exercices',
            exercises, solutions=False)
        sol_txt = self._render(
            f'Answer key - {_ascii(lesson.title)}',
            f'{level} - {subject} - Corrige',
            exercises, solutions=True)

        for kind, name, payload, order in (
            ('exercises', f'{base}-exercices.pdf', ex_txt, 900),
            ('corrige', f'{base}-corrige.pdf', sol_txt, 901),
        ):
            resource = Resource.objects.filter(
                lesson=lesson, file=f'resources/{name}').first()
            if resource is None:
                resource = Resource(lesson=lesson)
            resource.kind = Resource.Kind.PDF
            resource.order = order
            resource.title = (
                f'Practice worksheet - {lesson.title}' if kind == 'exercises'
                else f'Answer key - {lesson.title}')
            resource.title_fr = (
                'Fiche d\'exercices' if kind == 'exercises' else 'Corrige')
            resource.source_name = 'Mega Mighty Sixers'
            resource.license_note = ('Contenu original, diffusion libre aux '
                                     'membres de l\'association')
            resource.file.save(name, ContentFile(payload), save=False)
            resource.save()
        self.stdout.write(self.style.SUCCESS(
            f'[OK] {lesson.id} {lesson.title} : {len(exercises)} exercice(s)'))

    @staticmethod
    def _render(title, subtitle, exercises, solutions):
        out = io.BytesIO()
        pdf = _Worksheet(title, subtitle)
        pdf.add_page()
        if solutions:
            pdf.intro('Detailed method for every exercise. Follow the '
                      'substitutions line by line.',
                      'Corrige detaille de chaque exercice. Suis les '
                      'substitutions ligne par ligne.')
        else:
            pdf.intro('Complete each exercise on paper, writing every step of '
                      'your reasoning, then compare with the separate answer '
                      'key.',
                      'Fais chaque exercice sur une feuille en detaillant ton '
                      'raisonnement, puis compare avec le corrige separe.')
        for i, ex in enumerate(exercises, start=1):
            pdf.exercise(i, ex['enonce'])
            if solutions and ex['corrige']:
                pdf.solution(ex['corrige'])
        pdf.output(out)
        return out.getvalue()


class _Worksheet(FPDF):
    def __init__(self, title, subtitle):
        super().__init__(unit='mm', format='A4')
        self.title_txt = title
        self.subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=18)
        self.set_font('helvetica', '', 11)

    def header(self):
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 22, style='F')
        self.set_text_color(255, 215, 120)
        self.set_font('helvetica', 'B', 14)
        self.set_xy(10, 5)
        self.cell(0, 7, self.title_txt, new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(220, 226, 236)
        self.set_font('helvetica', '', 9)
        self.cell(0, 5, self.subtitle, new_x='LMARGIN', new_y='NEXT')
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_text_color(120, 128, 140)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 6, 'Mega Mighty Sixers - contenu original, diffusion '
                  'libre aux membres de l association', align='C')

    def intro(self, en, fr):
        self.set_text_color(30, 34, 42)
        self.set_font('helvetica', 'I', 10.5)
        self.multi_cell(0, 5.4, en, new_x='LMARGIN', new_y='NEXT')
        self.multi_cell(0, 5.4, fr, new_x='LMARGIN', new_y='NEXT')
        self.ln(4)

    def exercise(self, n, txt):
        self.ln(1)
        self.set_text_color(*PRIMARY)
        self.set_font('helvetica', 'B', 11)
        self.multi_cell(0, 6, f'{n}. {txt}', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin,
                  self.get_y())
        self.ln(2)

    def solution(self, txt):
        self.set_text_color(46, 125, 110)
        self.set_font('helvetica', '', 10.5)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5.4, txt, new_x='LMARGIN', new_y='NEXT')
        self.ln(3)
