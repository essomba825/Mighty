"""Délivrance automatique des cartes de membre."""

import secrets
from datetime import date, timedelta

from django.utils import timezone

from .models import MemberCard

# Alphabet sans caractères ambigus (0/O, 1/I/L, 5/S, 8/B, 2/Z)
ALPHABET = 'ACDEFGHJKMNPQRTUVWXY34679'


def _serial() -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(6))


def next_card_number() -> str:
    """Numéro unique du type MMS-2026-A3K9XZ."""
    while True:
        candidate = f'MMS-{date.today().year}-{_serial()}'
        if not MemberCard.objects.filter(card_number=candidate).exists():
            return candidate


def issue_card(profile, signed_by='', valid_months=12, force_new=False):
    """Crée la carte d'un profil si elle manque (ou la renouvelle).

    force_new=True regénère un nouveau numéro (carte perdue, radiée...).
    """
    card = getattr(profile, 'member_card', None)
    if card and not force_new:
        if not card.is_active or card.valid_until < date.today():
            card.valid_until = date.today() + timedelta(days=30 * valid_months)
            card.is_active = True
            if signed_by:
                card.signed_by = signed_by
            card.save(update_fields=['valid_until', 'is_active', 'signed_by'])
        return card

    card = card or MemberCard()
    card.profile = profile
    card.card_number = next_card_number()
    card.issued_at = timezone.now()
    card.valid_until = date.today() + timedelta(days=30 * valid_months)
    card.is_active = True
    if signed_by:
        card.signed_by = signed_by
    card.save()
    return card
