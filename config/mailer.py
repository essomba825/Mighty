"""Envoi d'emails transactionnels (HTML + texte) via les templates Django.

Chaque email vit dans `templates/email/<nom>.html` ET `templates/email/<nom>.txt`
(la version texte est le repli des clients qui n'affichent pas le HTML).

Règle absolue : un échec d'envoi ne casse JAMAIS la requête qui a déclenché
l'email (inscription, paiement...). On journalise et on retourne False.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def envoyer_email(destinataire, sujet, template, contexte=None):
    """Charge `email/<template>.{html,txt}` et envoie un message multipart.

    Retourne True si l'email est parti, False sinon (adresse absente,
    template manquant, SMTP injoignable...).
    """
    if not destinataire:
        return False
    try:
        contexte = {'site_url': settings.FRONTEND_URL, **(contexte or {})}
        html = render_to_string(f'email/{template}.html', contexte)
        texte = render_to_string(f'email/{template}.txt', contexte)
        message = EmailMultiAlternatives(
            sujet, texte, settings.DEFAULT_FROM_EMAIL, [destinataire],
        )
        message.attach_alternative(html, 'text/html')
        message.send()
        return True
    except Exception:
        logger.exception("Echec de l'envoi de l'email %r a %r", template, destinataire)
        return False
