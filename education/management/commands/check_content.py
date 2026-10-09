"""Audit du contenu pedagogique de toute la base.

Usage :
    python manage.py check_content
    python manage.py check_content --lesson 15
    python manage.py check_content --status published --strict
    python manage.py check_content --summary

`--strict` transforme les avertissements en erreurs (utile en CI ou avant
une mise en production).

Le code de sortie vaut 1 si au moins une erreur bloquante est detectee.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from education.content_quality import check_lesson
from education.models import Lesson


class Command(BaseCommand):
    help = "Controle qualite du contenu : traduction, correction, structure"

    def add_arguments(self, parser):
        parser.add_argument('--lesson', type=int,
                            help='Auditer une seule lecon par id')
        parser.add_argument('--status', choices=['draft', 'pending', 'published'],
                            help='Filtrer par statut')
        parser.add_argument('--strict', action='store_true',
                            help="Compter les avertissements comme des erreurs")
        parser.add_argument('--summary', action='store_true',
                            help='N\'afficher que le tableau de bord')
        parser.add_argument('--limit', type=int, default=40,
                            help='Nombre max de problemes affiches par lecon')

    def handle(self, *args, **options):
        qs = Lesson.objects.select_related('chapter__subject').prefetch_related(
            'steps__question__choices',
            'steps__question__hints',
            'quizzes__questions__choices',
            'quizzes__questions__hints',
        ).annotate(step_count=Count('steps', distinct=True))

        if options['lesson']:
            qs = qs.filter(pk=options['lesson'])
        if options['status']:
            qs = qs.filter(status=options['status'])

        total_errors = 0
        total_warnings = 0
        broken = []

        for lesson in qs.order_by('chapter__subject_id', 'chapter__order', 'order'):
            errors, warnings = [], []
            check_lesson(lesson, errors, warnings)

            # Coherence du statut : une lecon publiee doit etre complete.
            if lesson.status == 'published' and errors:
                errors = [f'[PUBLIEE - a corriger] {m}' for m in errors]

            if errors or warnings:
                broken.append((lesson, errors, warnings))
                total_errors += len(errors)
                total_warnings += len(warnings)

        total = qs.count()

        self.stdout.write('')
        self.stdout.write(f'Lecons auditees : {total}')
        self.stdout.write(f'  erreurs bloquantes : {total_errors}')
        self.stdout.write(f'  avertissements     : {total_warnings}')
        self.stdout.write('')

        if options['summary']:
            self._print_dashboard(qs, total_errors, total_warnings)
            # Un resume doit aussi etre exploitable en CI : meme code de sortie.
            self._exit_if_broken(total_errors, total_warnings, options['strict'])
            return

        limit = options['limit']
        for lesson, errors, warnings in broken:
            head = (f'Lecon {lesson.id} — {lesson.title} '
                    f'[{lesson.status}, {lesson.step_count} etape(s)]')
            self.stdout.write(self.style.MIGRATE_HEADING(head))
            for message in errors[:limit]:
                self.stdout.write(self.style.ERROR(f'  ERREUR  {message}'))
            if len(errors) > limit:
                self.stdout.write(f'  ... et {len(errors) - limit} autres erreurs')
            for message in warnings[:limit]:
                self.stdout.write(self.style.WARNING(f'  avertis. {message}'))
            if len(warnings) > limit:
                self.stdout.write(
                    f'  ... et {len(warnings) - limit} autres avertissements')
            self.stdout.write('')

        self._print_dashboard(qs, total_errors, total_warnings)
        self._exit_if_broken(total_errors, total_warnings, options['strict'])

    def _exit_if_broken(self, total_errors, total_warnings, strict):
        """Termine le processus avec un code d'erreur exploitable en CI.

        `CommandError` porte le message sur stderr, contrairement a
        `self.stderr.write`, et Django le convertit en `sys.exit(1)`.
        """
        if total_errors or (strict and total_warnings):
            detail = f'{total_errors} erreur(s)'
            if strict and total_warnings:
                detail += f', {total_warnings} avertissement(s) (--strict)'
            raise CommandError(
                f'CONTROLE QUALITE : ECHEC — {detail}. Contenu non publiable '
                f'en l\'etat.')
        self.stdout.write(self.style.SUCCESS('CONTROLE QUALITE : OK'))

    def _print_dashboard(self, qs, total_errors, total_warnings):
        stats = qs.aggregate(
            publiees=Count('pk', filter=None),
        )
        sans_etapes = qs.filter(steps__isnull=True).distinct().count()
        sans_obj = qs.filter(objectives=[]).distinct().count()
        publiees_sans_etapes = qs.filter(status='published', steps__isnull=True).distinct().count()

        self.stdout.write(self.style.MIGRATE_HEADING('Tableau de bord'))
        self.stdout.write(f'  lecons sans micro-etapes      : {sans_etapes}/{stats["publiees"]}')
        self.stdout.write(f'  lecons sans objectifs        : {sans_obj}/{stats["publiees"]}')
        self.stdout.write(f'  PUBLIEES sans micro-etapes   : {publiees_sans_etapes}')
        self.stdout.write('')
