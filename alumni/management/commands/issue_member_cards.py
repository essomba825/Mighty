"""Génère les cartes de membre manquantes.

Usage :
    python manage.py issue_member_cards                 # crée les cartes manquantes
    python manage.py issue_member_cards --force-new    # régénère tous les numéros
    python manage.py issue_member_cards --signed-by "Président de l'association"
"""

from django.core.management.base import BaseCommand

from alumni.cards import issue_card
from alumni.models import AlumniProfile


class Command(BaseCommand):
    help = 'Génère ou renouvelle les cartes de membre.'

    def add_arguments(self, parser):
        parser.add_argument('--force-new', action='store_true',
                            help=' attribue un nouveau numéro à chaque carte')
        parser.add_argument('--signed-by', default='', help='Nom du signataire')
        parser.add_argument('--months', type=int, default=12, help='Durée de validité (mois)')
        parser.add_argument('--only-missing', action='store_true',
                            help='Ignore les cartes existantes')

    def handle(self, *args, **options):
        created = renewed = 0
        for profile in AlumniProfile.objects.select_related('user').all():
            had_card = hasattr(profile, 'member_card')
            card = issue_card(
                profile,
                signed_by=options['signed_by'],
                valid_months=options['months'],
                force_new=options['force_new'],
            )
            if had_card:
                renewed += 1
            else:
                created += 1
            self.stdout.write(f'  {card.card_number} — {card.profile.user.get_full_name()}')
        self.stdout.write(self.style.SUCCESS(
            f'Terminé : {created} carte(s) créée(s), {renewed} renouvelée(s).'))
