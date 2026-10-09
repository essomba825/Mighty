"""Envoi de poussées Web (spec Push API / VAPID) vers les abonnements.

Trois règles :
- jamais d'exception qui remonte : le push est un bonus, il ne doit pas faire
  échouer l'opération métier (inscription, paiement...) qui le déclenche ;
- un abonnement expiré (404/410 renvoyé par le service de push du navigateur)
  est supprimé de la base ;
- sans clé VAPID ni module pywebpush installé, on journalise et on renonce.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Codes HTTP du service de push signifiant « cet abonnement n'existe plus ».
_ABONNEMENT_MORT = (404, 410)


def envoyer_poussee(users, titre, corps, url='/'):
    """Pousse une notification aux abonnements des `users` donnés.

    Retourne le nombre d'envois réussis (0 si push indisponible).
    """
    try:
        from pywebpush import WebPushException, webpush

        from .models import PushSubscription

        if not settings.VAPID_PRIVATE_KEY:
            logger.info('Push ignore : VAPID_PRIVATE_KEY non configure.')
            return 0

        abonnements = list(PushSubscription.objects.filter(user__in=list(users)))
        if not abonnements:
            return 0

        charge = json.dumps({'title': titre, 'body': corps, 'url': url},
                            ensure_ascii=False)
        envois = 0
        for abonnement in abonnements:
            try:
                webpush(
                    subscription_info={
                        'endpoint': abonnement.endpoint,
                        'keys': {'p256dh': abonnement.p256dh,
                                 'auth': abonnement.auth},
                    },
                    data=charge,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={'sub': settings.VAPID_CONTACT},
                    ttl=3600,
                )
                envois += 1
            except WebPushException as exc:
                code = getattr(getattr(exc, 'response', None), 'status_code', None)
                if code in _ABONNEMENT_MORT:
                    abonnement.delete()
                else:
                    logger.warning('Poussee refusee (%s) : %s', code, exc)
        return envois
    except Exception:
        logger.exception('Echec des poussees web.')
        return 0
