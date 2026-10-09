"""Exporte une lecon existante au format `author_lesson`.

Usage :
    python manage.py dump_lesson 15 > lecon.json
    python manage.py dump_lesson 15 --output education/content/lesson_15.json

Le fichier obtenu est lisible par `author_lesson` sans aucun changement :
c'est le miroir de la base, donc rejouer l'export puis l'importer ne change
rien. Toutes les etapes, questions, choix et indices sont en double langue,
y compris les champs FR vides (""), qui restent donc visibles a completer.
"""
import json

from django.core.management.base import BaseCommand, CommandError

from education.models import Lesson


def _question_payload(question):
    return {
        'kind': question.kind,
        'text': question.text or '',
        'text_fr': question.text_fr or '',
        'explanation': question.explanation or '',
        'explanation_fr': question.explanation_fr or '',
        'hint_prompt': question.hint_prompt or '',
        'hint_prompt_fr': question.hint_prompt_fr or '',
        'difficulty': question.difficulty,
        'config': question.config or {},
        'choices': [
            {'text': c.text or '', 'text_fr': c.text_fr or '',
             'correct': c.is_correct}
            for c in question.choices.all()
        ],
        'hints': [
            {'text': h.text or '', 'text_fr': h.text_fr or ''}
            for h in question.hints.all().order_by('order')
        ],
    }


class Command(BaseCommand):
    help = 'Exporte une lecon au format JSON accepte par author_lesson'

    def add_arguments(self, parser):
        parser.add_argument('lesson', type=int, help='Id de la lecon a exporter')
        parser.add_argument('--output', help='Chemin du fichier a ecrire '
                                             '(stdout par defaut)')

    def handle(self, *args, **options):
        lesson_id = options['lesson']
        lesson = Lesson.objects.filter(pk=lesson_id).prefetch_related(
            'steps__question__choices', 'steps__question__hints',
            'quizzes__questions__choices', 'quizzes__questions__hints').first()
        if lesson is None:
            raise CommandError(f'Lecon {lesson_id} introuvable')

        pack = {
            'lesson': lesson.id,
            'status': lesson.status,
            'lesson_fields': {
                'title': lesson.title or '',
                'title_fr': lesson.title_fr or '',
                'summary': lesson.summary or '',
                'summary_fr': lesson.summary_fr or '',
                'objectives': lesson.objectives or [],
                'objectives_fr': lesson.objectives_fr or [],
                'content': lesson.content or '',
                'content_fr': lesson.content_fr or '',
            },
            'steps': [
                {
                    'kind': s.kind,
                    'title': s.title or '',
                    'title_fr': s.title_fr or '',
                    'content': s.content or '',
                    'content_fr': s.content_fr or '',
                    'required': s.required,
                    'xp': s.xp,
                    **({'question': _question_payload(s.question)}
                       if s.question_id else {}),
                }
                for s in lesson.steps.all().order_by('order')
            ],
        }

        quiz = lesson.quizzes.first()
        if quiz:
            pack['quiz'] = {
                'title': quiz.title or '',
                'title_fr': quiz.title_fr or '',
                'pass_score': quiz.pass_score,
                'questions': [_question_payload(q)
                              for q in quiz.questions.order_by('order')],
            }

        text = json.dumps(pack, ensure_ascii=False, indent=2) + '\n'
        destination = options.get('output')
        if destination:
            with open(destination, 'w', encoding='utf-8') as f:
                f.write(text)
            self.stdout.write(self.style.SUCCESS(
                f'[OK] {lesson.title} -> {destination}'))
        else:
            self.stdout.write(text)
