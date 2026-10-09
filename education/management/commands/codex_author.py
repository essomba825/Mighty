"""Fait rediger un pack de lecon par Codex, puis l'ecrit proprement.

C'est la reponse au probleme historique du projet : le contenu etait genere par
ollama/gemma2:2b, qui melangeait le francais dans les champs anglais. Ici le
schema JSON et les regles de `education.content_quality` sont injectes tels
quels dans le prompt, donc le modele ecrit contre la vraie source de verite et
non d'apres un resume.

Usage :
    python manage.py codex_author --list
    python manage.py codex_author --subject chemistry-al --chapter 1 --lesson 1 \
        --title "Molar concentration and solutions" \
        --objective "Calculate and dilute molar solutions" --dry-run
    python manage.py codex_author --subject biology-ol --chapter 1 --lesson 1 \
        --title "The structure of the cell" --apply

`--apply` enchaîne `author_lesson`, qui annule l'ecriture si le controle
qualite echoue : impossible de publier un contenu melee.
"""
import re
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from education import codex_client as cx
from education.content_quality import ENGLISH_MARKERS, FRENCH_MARKERS, \
    FRENCH_RATIO, ENGLISH_RATIO
from education.models import Chapter, Lesson, Subject


def _mots(regex):
    """Liste les mots-cles d'une regex de detection, pour les lister au modele.

    On relit le source de la regex plutot que d'appliquer FRENCH_MARKERS :
    appliquer ne donnerait que les mots effectivement presents dans une chaine
    donnee, alors qu'on veut la liste exhaustive a interdire.
    """
    source = regex.pattern
    if source.startswith('r"') or source.startswith("r'"):
        source = source[2:-1]
    return sorted({m for m in re.split(r'\|', source) if m and m.isalpha()})


SCHEMA = """{
  "lesson": <ID_ENTIER>,
  "status": "draft",
  "lesson_fields": {
    "title": "...", "title_fr": "...",
    "summary": "...", "summary_fr": "...",
    "content": "markdown", "content_fr": "markdown",
    "objectives": ["...", "..."],
    "objectives_fr": ["...", "..."]
  },
  "steps": [
    {
      "kind": "concept",
      "title": "...", "title_fr": "...",
      "content": "markdown", "content_fr": "markdown",
      "required": true, "xp": 10,
      "question": {
        "kind": "mcq",
        "difficulty": 1,
        "text": "...", "text_fr": "...",
        "explanation": "...", "explanation_fr": "...",
        "hint_prompt": "...", "hint_prompt_fr": "...",
        "config": {},
        "choices": [
          {"text": "...", "text_fr": "...", "correct": true}
        ],
        "hints": [{"text": "...", "text_fr": "..."}]
      }
    }
  ],
  "quiz": {
    "title": "...", "title_fr": "...",
    "pass_score": 60,
    "questions": [
      {
        "kind": "numeric", "difficulty": 1,
        "text": "...", "text_fr": "...",
        "explanation": "...", "explanation_fr": "...",
        "hint_prompt": "...", "hint_prompt_fr": "...",
        "config": {"accepted": [3.5], "tolerance": 0.01},
        "choices": [],
        "hints": [{"text": "...", "text_fr": "..."}]
      }
    ]
  }
}"""

REGLE_TYPES = """- step.kind in {concept, explain, example, practice, question, summary}
- question.kind in {mcq, numeric, text, ordered, pairing}
- a quiz question has EXACTLY the same shape as a step question
- mcq : >= 2 choices, EXACTLY one with "correct": true, no duplicate texts
- numeric : "config": {"accepted": [3.5], "tolerance": 0.01}
    `accepted` holds NUMBERS only. An entry that cannot be read as a number is
    silently dropped by the grader, and if it is the only one the question
    becomes impossible to pass. Never write "trois", "3,5" or "3 1/2" here.
- text : "config": {"accepted": ["x = 2"], "case_sensitive": false}
    `accepted` holds STRINGS only. Never use a text question to ask for a
    number: the grader compares digit sequences, so "84" would pass "4 x 3 x 7".
- ordered : "config": {"items": [...], "items_fr": [...]}, >= 2 items, no duplicate
- pairing : "config": {"pairs": [["terme","definition"], ...], "pairs_fr": [...]},
    no trivial pair, no repeated left term
- no choices on numeric/text/ordered/pairing questions"""

REGLE_QUALITE = """1. The pack MUST be valid JSON, nothing else. No markdown fences, no commentary.
2. Every `*_fr` field is written in natural French. Every plain field is written
   in natural English. A French sentence inside an English field is the single
   most common failure: it blocks publication.
3. The language check is mechanical. A text of 4 words or more fails if at least
   {fr_ratio:.0%} of its words come from this French list:
   {french}
   Conversely a French field fails if {en_ratio:.0%} of its words come from:
   {english}
   Short answers (numbers, formulas, symbols) are exempt. Write full sentences
   in explanatory fields.
4. `title`, `summary`, `content`, `objectives`, every step title/content, every
   question text and every choice must have a French counterpart.
5. `objectives` and `objectives_fr` must have the SAME number of items.
6. At least 5 steps and at least 4 quiz questions. At least one step required:true.
7. The maths must be correct. Numbers in the explanations must match the
   numbers in the answers. Vary the question kinds: use numeric where the answer
   is a number, mcq otherwise.
8. Markdown is allowed in `content` (## headings, tables, bullet lists). Keep
   each step content to 60-150 words so a teenager can read it in one screen."""


class Command(BaseCommand):
    help = "Fait rediger un pack de lecon par Codex, avec le schema et les regles"

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true',
                            help='Liste les matieres et leurs leçons')
        parser.add_argument('--subject', required=False)
        parser.add_argument('--chapter', type=int, default=1)
        parser.add_argument('--lesson', type=int, default=1)
        parser.add_argument('--title', required=False)
        parser.add_argument('--objective', action='append', default=[],
                            help='Objectif d\'apprentissage (repetable)')
        parser.add_argument('--chapter-title', default='')
        parser.add_argument('--level', default='',
                            help='Niveau pedagogique, ex "GCE OL", "GCE AL"')
        parser.add_argument('--steps', type=int, default=5)
        parser.add_argument('--questions', type=int, default=4)
        parser.add_argument('--model', default=cx.MODEL_DEFAULT)
        parser.add_argument('--effort', default='high',
                            choices=['low', 'medium', 'high'])
        parser.add_argument('--max-tokens', type=int, default=16000)
        parser.add_argument('--out', default='',
                            help='Chemin du pack ; sinon backend/education/content')
        parser.add_argument('--create', action='store_true',
                            help='Cree la matiere/chapitre/lecon manquante en draft')
        parser.add_argument('--apply', action='store_true',
                            help='Passe le pack a author_lesson')
        parser.add_argument('--dry-run', action='store_true',
                            help='Affiche le prompt, n\'appelle pas l\'API')
        parser.add_argument('--timeout', type=int, default=900)

    def handle(self, *args, **options):
        if options['list']:
            return self._lister()

        for champ in ('subject', 'title'):
            if not options[champ]:
                raise CommandError(f'--{champ} est obligatoire.')

        # Un apercu ne doit rien ecrire en base : sinon --create --dry-run
        # laisserait un chapitre et une lecon vides derriere lui.
        options['create'] = options['create'] and not options['dry_run']

        lecon = self._resoudre_lecon(options)
        prompt = self._construire_prompt(lecon, options)

        if options['dry_run']:
            self.stdout.write(prompt)
            return

        self.stderr.write(f'[codex] {lecon.id} · {lecon.title} · '
                          f'modele={options["model"]} effort={options["effort"]}')
        try:
            resultat = cx.chat(prompt, system=self._system(), model=options['model'],
                               effort=options['effort'],
                               max_output_tokens=options['max_tokens'],
                               timeout=options['timeout'])
        except cx.CodexError as exc:
            raise CommandError(str(exc)) from exc

        try:
            pack = cx.extract_json(resultat['text'])
        except (cx.CodexError, ValueError) as exc:
            raise CommandError(f'Reponse illisible : {exc}') from exc

        self._valider_structure(pack, lecon)
        pack['lesson'] = lecon.id
        pack['status'] = 'draft'

        import json
        chemin = Path(options['out']) if options['out'] else self._chemin_defaut(
            lecon)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(pack, ensure_ascii=False, indent=2),
                          encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'[OK] {chemin}'))

        if options['apply']:
            call_command('author_lesson', str(chemin))
        else:
            self.stdout.write(
                f'Rejouer avec : python manage.py author_lesson "{chemin}"')

        usage = resultat.get('usage') or {}
        self.stderr.write(self.style.WARNING(
            f'modele={resultat.get("model")} tokens_in={usage.get("input_tokens")} '
            f'tokens_out={usage.get("output_tokens")}'))

    # ------------------------------------------------------------------
    def _lister(self):
        for subject in Subject.objects.all():
            lecons = Lesson.objects.filter(chapter__subject=subject)
            publiees = lecons.filter(status='published').count()
            self.stdout.write(
                f'{subject.slug:20} chapitres={subject.chapters.count()} '
                f'lecons={lecons.count()} publiees={publiees} '
                f'vides={lecons.filter(steps__isnull=True).count()}')
            for chapitre in subject.chapters.all():
                for lecon in chapitre.lessons.all():
                    self.stdout.write(
                        f'    ch{chapitre.order} lo{lecon.order} '
                        f'id={lecon.id:<4} [{lecon.status:<9}] '
                        f'etapes={lecon.steps.count():<3} {lecon.title}')

    def _resoudre_lecon(self, options):
        try:
            subject = Subject.objects.get(slug=options['subject'])
        except Subject.DoesNotExist as exc:
            raise CommandError(
                f'Matiere inconnue : {options["subject"]}. '
                f'Utilise --list pour voir les slugs.') from exc

        chapitre = subject.chapters.filter(order=options['chapter']).first()
        if chapitre is None and options['create']:
            chapitre = self._creer_chapitre(subject, options)

        if chapitre is None:
            raise CommandError(
                f'La matiere {subject.slug} n\'a pas de chapitre '
                f'{options["chapter"]}. Relance avec --create.')

        lecon = chapitre.lessons.filter(order=options['lesson']).first()
        if lecon is None and options['create']:
            lecon = self._creer_lecon(chapitre, options)
        if lecon is None:
            if options['dry_run']:
                return self._lecon_fantome(options)
            raise CommandError(
                f'Pas de leçon {options["lesson"]} dans le chapitre '
                f'{options["chapter"]}. Relance avec --create.')
        return lecon

    def _lecon_fantome(self, options):
        """Lecon non persistee, pour apercu du prompt sans toucher la base."""
        from types import SimpleNamespace
        try:
            subject = Subject.objects.get(slug=options['subject'])
        except Subject.DoesNotExist as exc:
            raise CommandError(f'Matiere inconnue : {options["subject"]}'
                               ) from exc
        chapitre = SimpleNamespace(
            order=options['chapter'],
            title=options['chapter_title'] or f'Chapter {options["chapter"]}',
            subject=subject)
        lecon = SimpleNamespace(id=0, title=options['title'], chapter=chapitre)
        self.stderr.write('[codex] APERCU : aucune ecriture, lecon id 0')
        return lecon

    @transaction.atomic
    def _creer_chapitre(self, subject, options):
        titre = options['chapter_title'] or f'Chapter {options["chapter"]}'
        self.stderr.write(f'[codex] creation du chapitre « {titre} »')
        return Chapter.objects.create(subject=subject, order=options['chapter'],
                                      title=titre, title_fr=titre)

    @transaction.atomic
    def _creer_lecon(self, chapitre, options):
        self.stderr.write(
            f'[codex] creation de la lecon « {options["title"]} » en draft')
        return Lesson.objects.create(
            chapter=chapitre, order=options['lesson'],
            title=options['title'], title_fr=options['title'],
            status='draft')

    def _chemin_defaut(self, lecon):
        base = Path(__file__).resolve().parents[3] / 'content'
        slug = re.sub(r'[^a-z0-9]+', '_',
                      lecon.title.lower()).strip('_')[:40]
        return base / f'lesson_{lecon.id}_{slug}.json'

    def _system(self):
        return (
            'You are a senior GCE science teacher writing bilingual '
            '(English + French) courseware. You return strictly valid JSON and '
            'nothing else. You never mix French words into English fields nor '
            'English words into French fields. You compute correct numbers.')

    def _construire_prompt(self, lecon, options):
        objectifs = options['objective'] or [
            'Understand the main idea',
            'Apply it to a worked example',
            'Check your own answer']

        return f"""Write the GCE lesson pack for lesson id {lecon.id}.

SUBJECT   : {lecon.chapter.subject.name} ({lecon.chapter.subject.level}, {lecon.chapter.subject.slug})
LEVEL     : {options['level'] or 'GCE OL / AL, secondary school'}
CHAPTER   : {lecon.chapter.title} (chapter {lecon.chapter.order})
LESSON    : {options['title']}
OBJECTIVES:
{chr(10).join('- ' + o for o in objectifs)}

DELIVER: {options['steps']} steps and {options['questions']} quiz questions.

JSON SCHEMA (the only accepted shape):
{SCHEMA}

VALID `kind` VALUES
{REGLE_TYPES}

MANDATORY QUALITY RULES
{REGLE_QUALITE.format(
    fr_ratio=FRENCH_RATIO, en_ratio=ENGLISH_RATIO,
    french=' '.join(_mots(FRENCH_MARKERS)),
    english=' '.join(_mots(ENGLISH_MARKERS)))}

Answer with the JSON object only."""

    def _valider_structure(self, pack, lecon):
        erreurs = []
        if not isinstance(pack, dict):
            raise CommandError('La reponse n\'est pas un objet JSON.')

        steps = pack.get('steps')
        if not isinstance(steps, list) or not steps:
            erreurs.append('"steps" absent ou vide')
        quiz = pack.get('quiz') or {}
        questions = quiz.get('questions')
        if not isinstance(questions, list) or not questions:
            erreurs.append('"quiz.questions" absent ou vide')

        if not erreurs:
            if len(steps) < 3:
                erreurs.append(f'seulement {len(steps)} etapes (minimum 3)')
            if len(questions) < 3:
                erreurs.append(
                    f'seulement {len(questions)} questions de quiz (minimum 3)')

            for i, step in enumerate(steps, start=1):
                titre = (step.get('title') or '').strip()
                contenu = (step.get('content') or '').strip()
                if not titre:
                    erreurs.append(f'etape{i} : titre manquant')
                if not contenu:
                    erreurs.append(f'etape{i} : contenu manquant')
                question = step.get('question')
                if question:
                    erreurs.extend(self._valider_question(question,
                                                          f'etape{i}'))

            for i, question in enumerate(questions, start=1):
                erreurs.extend(self._valider_question(question, f'quiz{i}'))

        if erreurs:
            liste = '\n'.join(f'  - {e}' for e in erreurs)
            raise CommandError(f'Pack invalide, rien n\'a ete ecrit :\n{liste}')

    def _valider_question(self, question, prefixe):
        erreurs = []
        if not isinstance(question, dict):
            return [f'{prefixe} : question pas un objet']
        if not (question.get('text') or '').strip():
            erreurs.append(f'{prefixe} : enonce manquant')
        kind = question.get('kind', 'mcq')
        if kind == 'mcq':
            choix = question.get('choices') or []
            if len(choix) < 2:
                erreurs.append(f'{prefixe} : QCM avec moins de 2 choix')
            corrects = sum(1 for c in choix if c.get('correct'))
            if corrects != 1:
                erreurs.append(f'{prefixe} : {corrects} bonne(s) reponse(s), '
                               f'1 attendue')
        elif kind in ('numeric', 'text'):
            accepted = (question.get('config') or {}).get('accepted')
            if not isinstance(accepted, list) or not accepted:
                erreurs.append(f'{prefixe} : config {kind} sans "accepted"')
        elif kind == 'ordered':
            config = question.get('config') or {}
            if len(config.get('items') or []) < 2:
                erreurs.append(f'{prefixe} : config ordre sans 2 elements')
        elif kind == 'pairing':
            config = question.get('config') or {}
            if not config.get('pairs'):
                erreurs.append(f'{prefixe} : config appariement sans "pairs"')
        return erreurs