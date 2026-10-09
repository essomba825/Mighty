"""Ecriture dans le journal d'activite (§9).

Un helper plutot qu'un middleware, parce que le middleware ne peut pas dire
*ce qui* a ete modifie ni *qui* l'a demande quand la requete echoue ou quand
elle est faite par un script. Ici l'appel est explicite et porte la faute, donc
ce qui est oublie est visible dans la relecture du code.

Regle de conception : `record()` ne leve jamais. Un journal qui casse la
requete qu'il est cense documenter est pire qu'un journal absent — il
transforme une erreur fonctionnelle en erreur serveur.
"""
from accounts.models import ActivityLog


def _request_ip(request):
    if request is None:
        return None
    # X-Forwarded-For n'est lu que si le proxy est devant. On retient la
    # premiere valeur, qui est le client d'origine dans une chaine de proxies
    # correctement configuree.
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def record(request=None, *, action, model_name='', object_id='', summary='',
          actor=None):
    """Ajoute une entree. Ne leve jamais : renvoie l'objet ou None."""
    if actor is None:
        actor = getattr(request, 'user', None)
        if actor is not None and not getattr(actor, 'is_authenticated', False):
            actor = None

    label = ''
    if actor is not None:
        label = (actor.get_full_name() or actor.get_username() or '').strip()

    try:
        return ActivityLog.objects.create(
            actor=actor,
            actor_label=label[:150],
            action=action,
            model_name=(model_name or '')[:100],
            object_id=str(object_id)[:64] if object_id not in (None, '') else '',
            summary=summary[:255],
            ip_address=_request_ip(request),
        )
    except Exception:
        # Journal indisponible = on continue. Voir la note de module.
        return None