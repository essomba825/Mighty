"""Author a lesson as micro-steps (idempotent).

Usage :
    python manage.py author_lesson education/content/math_16_fractions.json
    python manage.py author_lesson <file> --dry-run
    python manage.py author_lesson <file> --force

The JSON file is the source of truth. Running it twice changes nothing.
The JSON is validated before the first write, then `content_quality` runs on
the persisted lesson: if it reports a blocking error the whole transaction is
rolled back, so a broken lesson never lands in the database. `--force` keeps
the write and only reports.

JSON shape:
{
  "lesson": 16,                    # lesson id to author into
  "status": "published",           # optional, default: keep current
  "lesson_fields": {               # optional metadata fixes
    "summary_fr": "..."
  },
  "steps": [
    {
      "kind": "concept",           # concept|explain|example|practice|question|summary
      "title": "...", "title_fr": "...",
      "content": "...", "content_fr": "...",
      "required": true, "xp": 10,
      "question": {                # optional
        "kind": "mcq",             # mcq|numeric|text|ordered|pairing
        "text": "...", "text_fr": "...",
        "explanation": "...", "explanation_fr": "...",
        "hint_prompt": "...", "hint_prompt_fr": "...",
        "config": {"accepted": [3]},
        "choices": [
          {"text": "7", "text_fr": "7", "correct": false}
        ],
        "hints": [
          {"text": "...", "text_fr": "..."}
        ]
      }
    }
  ],
  "quiz": {                        # optional end-of-lesson quiz
    "title": "...", "title_fr": "...",
    "pass_score": 60,
    "questions": [ { ...same as question... } ]
  }
}
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from education.models import Choice, Hint, Lesson, Question, Quiz, Step

STEP_KINDS = {k for k, _ in Step.Kind.choices}
QUESTION_KINDS = {k for k, _ in Question.Kind.choices}


def apply_question(payload, errors, *, quiz=None, step=None, order=1):
    """Cree ou met a jour une question. Ne committe rien : l'appelant
    persiste dans une transaction."""
    prefix = f'Q{order}'
    kind = payload.get('kind', 'mcq')
    if kind not in QUESTION_KINDS:
        errors.append(f'{prefix} : type de question inconnu {kind!r}')
        return None

    text = payload.get('text', '').strip()
    if not text:
        errors.append(f'{prefix} : enonce manquant')
        return None

    if quiz is not None:
        question = quiz.questions.filter(order=order).first()
        if question is None:
            question = Question(quiz=quiz, order=order)
    else:
        # Une question d'etape n'appartient ni au quiz ni a une lecon : elle est
        # attachee par le OneToOne de `Step`. On met a jour la question deja
        # attachee, sinon le re-jeu du meme JSON tomberait sur `order` et
        # retacherait la question a une autre etape — UNIQUE est violated,
        # puisqu'une question ne peut appartenir qu'a une seule etape.
        question = step.question
        if question is None:
            question = Question.objects.filter(
                step__lesson=step.lesson, order=order).first()
        if question is None:
            question = Question(quiz=None, order=order)

    question.kind = kind
    question.text = text
    question.text_fr = payload.get('text_fr', '').strip()
    question.explanation = payload.get('explanation', '').strip()
    question.explanation_fr = payload.get('explanation_fr', '').strip()
    question.hint_prompt = payload.get('hint_prompt', '').strip()
    question.hint_prompt_fr = payload.get('hint_prompt_fr', '').strip()
    question.difficulty = int(payload.get('difficulty', 1))
    question.config = payload.get('config') or {}
    # Il faut une cle primaire avant de toucher aux relations (choices, hints).
    question.save()
    if step is not None and step.question_id != question.id:
        step.question = question
        step.save(update_fields=['question'])

    # Choix : on repart d'une liste propre pour refleter exactement le JSON.
    if kind == 'mcq':
        existing = {c.id: c for c in question.choices.all()}
        keep = set()
        corrects = 0
        for raw in payload.get('choices', []):
            texte = str(raw.get('text', '')).strip()
            if not texte:
                errors.append(f'{prefix} : choix vide')
                continue
            correct = bool(raw.get('correct'))
            corrects += 1 if correct else 0
            match = next((c for c in existing.values()
                          if c.text == texte and c.id not in keep), None)
            if match is None:
                match = Choice(question=question, text=texte)
            match.text = texte
            match.text_fr = str(raw.get('text_fr', '') or texte).strip()
            match.is_correct = correct
            match.save()
            keep.add(match.id)
        for cid, choice in existing.items():
            if cid not in keep:
                choice.delete()
        if corrects != 1:
            errors.append(f'{prefix} : {corrects} bonne(s) reponse(s) QCM, '
                          f'1 attendue')

    # Indices : on repart d'une liste propre pour refleter exactement le JSON.
    for hint in question.hints.all():
        hint.delete()
    for index, raw in enumerate(payload.get('hints', []), start=1):
        texte = str(raw.get('text', '')).strip()
        if not texte:
            continue
        Hint.objects.create(
            question=question, order=index, text=texte,
            text_fr=str(raw.get('text_fr', '') or texte).strip())

    return question


class Command(BaseCommand):
    help = "Ecrit le contenu d'une lecon (micro-etapes + quiz) de facon idempotente"

    def add_arguments(self, parser):
        parser.add_argument('content', help='Fichier JSON decrivant la lecon')
        parser.add_argument('--dry-run', action='store_true',
                            help='Valide et affiche sans ecrire en base')
        parser.add_argument('--force', action='store_true',
                            help='Ecrit malgre des erreurs bloquantes')

    @transaction.atomic
    def handle(self, *args, **options):
        path = options['content']
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Fichier introuvable : {path}')
        except json.JSONDecodeError as exc:
            raise CommandError(f'JSON invalide : {exc}')

        lesson_id = data.get('lesson')
        lesson = Lesson.objects.filter(pk=lesson_id).select_related(
            'chapter__subject').first()
        if lesson is None:
            raise CommandError(f'Lecon {lesson_id} introuvable')

        errors = []
        steps_payload = data.get('steps') or []
        if not steps_payload:
            errors.append('aucune micro-etape dans le fichier')

        # 1) Validation du JSON seul, avant toute ecriture.
        for index, payload in enumerate(steps_payload, start=1):
            kind = payload.get('kind', 'concept')
            if kind not in STEP_KINDS:
                errors.append(f'etape{index} : type inconnu {kind!r}')
            if not (payload.get('title') or '').strip():
                errors.append(f'etape{index} : titre manquant')
            if not (payload.get('content') or '').strip():
                errors.append(f'etape{index} : contenu manquant')
            question = payload.get('question')
            if question is not None:
                if not (question.get('text') or '').strip():
                    errors.append(f'etape{index} : enonce manquant')
                elif question.get('kind') == 'mcq':
                    choices = question.get('choices') or []
                    if len(choices) < 2:
                        errors.append(f'etape{index} : moins de 2 choix')
                    if sum(1 for c in choices if c.get('correct')) != 1:
                        errors.append(f'etape{index} : une seule bonne '
                                      f'reponse attendue')

        if errors and not options['force']:
            self._report_errors(lesson, errors)
            raise CommandError(
                f'{len(errors)} erreur(s) bloquante(s) — rien n\'a ete ecrit. '
                f'Use --force pour ecrire quand meme.')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'[DRY-RUN] {lesson.title} : {len(steps_payload)} etape(s) '
                f'seraient ecrites. JSON valide.'))
            return

        # 2) Metadonnees de la lecon.
        for field, value in (data.get('lesson_fields') or {}).items():
            if hasattr(lesson, field):
                setattr(lesson, field, value)
        nouveau_statut = data.get('status')
        if nouveau_statut in dict(Lesson.Status.choices):
            lesson.status = nouveau_statut
        lesson.save()

        # 3) Etapes. On ne supprime pas les etapes existantes au-dela du
        #    fichier : le JSON est complet, donc on synchronise exactement.
        wanted = set()
        for index, payload in enumerate(steps_payload, start=1):
            step = lesson.steps.filter(order=index).first()
            if step is None:
                step = Step(lesson=lesson, order=index)
            step.order = index
            step.kind = payload.get('kind', 'concept')
            step.title = payload.get('title', '').strip()[:200]
            step.title_fr = payload.get('title_fr', '').strip()[:200]
            step.content = payload.get('content', '')
            step.content_fr = payload.get('content_fr', '')
            step.required = bool(payload.get('required', False))
            step.xp = int(payload.get('xp', 10))
            step.save()
            wanted.add(step.id)

            question_payload = payload.get('question')
            if question_payload:
                apply_question(question_payload, errors, step=step, order=index)
            elif step.question_id:
                step.question.delete()
                step.question = None
                step.save()

        obsolete = lesson.steps.exclude(pk__in=wanted)
        count_supprimes = obsolete.count()
        for step in obsolete:
            if step.question_id:
                step.question.delete()
            step.delete()

        # 4) Quiz de fin de lecon : un seul par lecon, remplace integralement.
        quiz_payload = data.get('quiz')
        quiz_written = 0
        if quiz_payload:
            quiz = lesson.quizzes.first()
            if quiz is None:
                quiz = Quiz(lesson=lesson, title=lesson.title)
            quiz.title = quiz_payload.get('title') or lesson.title
            quiz.title_fr = quiz_payload.get('title_fr', '')
            quiz.pass_score = int(quiz_payload.get('pass_score', 60))
            quiz.save()
            # On NE supprime pas les questions existantes : `apply_question`
            # les met a jour par `order`, ce qui conserve les id et donc
            # l'historique des tentatives deja enregistrees. Les questions
            # devenues inutiles sont retirees a la fin.
            # On garde explicitement les ids que la regenere cree. L'utilisation
            # liee du meme order sur plusieurs questions anciennes garde les
            # orphelines silencieusement, il faut suivre les ids'.
            kept_ids = set()
            for index, payload in enumerate(quiz_payload.get('questions') or [],
                                             start=1):
                q = apply_question(payload, errors, quiz=quiz, order=index)
                quiz_written += 1
                if q is not None:
                    kept_ids.add(q.id)
            for question in quiz.questions.exclude(pk__in=kept_ids):
                question.delete()

        self.stdout.write(self.style.SUCCESS(
            f'[OK] {lesson.title} : {len(steps_payload)} etape(s), '
            f'{quiz_written} question(s) de quiz'
            + (f', {count_supprimes} etape(s) obsolete(s) supprimee(s)'
               if count_supprimes else '')))

        # 5) Controle qualite final, une fois les donnees en base.
        from education.content_quality import check_lesson
        from django.db import connection
        from django.db.models import Count

        lesson = (Lesson.objects.filter(pk=lesson.pk)
                  .prefetch_related(
                      'steps__question__choices', 'steps__question__hints',
                      'quizzes__questions__choices', 'quizzes__questions__hints')
                  .annotate(step_count=Count('steps'))[0])
        final_errors, final_warnings = [], []
        check_lesson(lesson, final_errors, final_warnings)

        for message in final_errors:
            self.stdout.write(self.style.ERROR(f'  ERREUR  {message}'))
        for message in final_warnings:
            self.stdout.write(self.style.WARNING(f'  avertis. {message}'))
        if final_errors:
            self.stdout.write(self.style.ERROR(
                f'CONTROLE QUALITE : {len(final_errors)} erreur(s) — lecon '
                f'a corriger avant publication.'))
            if not options['force']:
                # `@transaction.atomic` annule tout : l'eleve ne voit jamais une
                # lecon a moitie ecrite, et l'identifiant de la lecon reste
                # utilisable meme si l'on rejoue le fichier apres correction.
                raise CommandError(
                    f'{len(final_errors)} erreur(s) de qualite — ecriture '
                    f'annulee. Corrige le JSON ou utilise --force.')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'CONTROLE QUALITE : OK ({len(final_warnings)} avertissement(s))'))

    def _report_errors(self, lesson, errors):
        self.stdout.write(self.style.ERROR(
            f'Validation echouee pour « {lesson.title} » :'))
        for message in errors:
            self.stdout.write(self.style.ERROR(f'  - {message}'))
