"""Aiguillage des notifications pour les trois événements métier :
création de compte, demande de mentorat, paiement d'une contribution.

Chaque événement déclenche jusqu'à trois canaux :
1. un email transactionnel (destinataire : le membre concerné) ;
2. une notification interne (in-app) pour chaque administrateur ;
3. une poussée web (push) vers les administrateurs et le membre concerné.

Règle commune : aucune fonction ci-dessous ne lève. Elles sont appelées au
cœur de réponses HTTP (inscription, vérification de paiement...) : un souci
de notification ne doit jamais faire échouer l'opération métier.
"""

import logging

logger = logging.getLogger(__name__)


def _admins():
    """Tous les destinataires d'alertes de gestion : staff et rôles admin."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    User = get_user_model()
    return User.objects.filter(Q(is_staff=True) | Q(role='admin')).distinct()


def notifier_admins(titre, message, lien=''):
    """Notification interne (visible sur /notifications) pour chaque admin."""
    try:
        from .models import Notification

        cibles = list(_admins())
        Notification.objects.bulk_create([
            Notification(user=admin, title=titre, message=message, link=lien)
            for admin in cibles
        ])
        return len(cibles)
    except Exception:
        logger.exception("Notification admin impossible : %r", titre)
        return 0


def _email(destinataire, sujet, template, contexte):
    try:
        from config.mailer import envoyer_email
        envoyer_email(destinataire, sujet, template, contexte)
    except Exception:
        logger.exception("Email %r impossible.", template)


def _poussee(users, titre, corps, url='/'):
    try:
        from .push import envoyer_poussee
        envoyer_poussee(users, titre, corps, url)
    except Exception:
        logger.exception("Poussee impossible : %r", titre)


# ---------------------------------------------------------------- evenements


def apres_inscription(utilisateur):
    """Compte créé (statut pending) : email de bienvenue + alerte admin."""
    prenom = utilisateur.first_name or ''
    nom = utilisateur.get_full_name() or utilisateur.username
    _email(
        utilisateur.email,
        'Bienvenue sur Mega Mighty Sixers — validation de votre compte',
        'inscription_recue',
        {'prenom': prenom},
    )
    message = (f'{nom} vient de s’inscrire. Le compte est en attente '
               f'de validation dans /admin/membres.')
    notifier_admins('Nouveau compte à valider', message, '/admin/membres')
    _poussee(_admins(), 'Nouveau compte à valider', nom, '/admin/membres')


def apres_demande_mentorat(demande):
    """Demande de mentorat créée : accusé au mentée + alerte admin + push."""
    offre = demande.offer
    mentor = offre.mentor
    mentee = demande.mentee
    domaine = offre.field
    nom_mentor = mentor.get_full_name() or mentor.username
    nom_mentee = mentee.get_full_name() or mentee.username

    _email(
        mentee.email,
        'Votre demande de mentorat a bien été envoyée',
        'demande_mentorat',
        {'prenom': mentee.first_name or '', 'mentor': nom_mentor,
         'domaine': domaine},
    )
    message = (f'{nom_mentee} demande à être mentoré en « {domaine} » '
               f'par {nom_mentor}.')
    notifier_admins('Nouvelle demande de mentorat 🤝', message, '/mentorat')
    # Le mentor notifié en interne par la vue reçoit aussi la poussée.
    _poussee(list(_admins()) + [mentor],
             'Nouvelle demande de mentorat 🤝', message, '/mentorat')


def _notifie(utilisateur, titre, message, lien='/mentorat'):
    """Notification interne d'un membre, sans jamais faire échouer l'appelant."""
    try:
        from .models import Notification
        Notification.objects.create(
            user=utilisateur, title=titre, message=message, link=lien)
    except Exception:
        logger.exception('Notification %r impossible.', titre)


def apres_mentorat_accepte(demande):
    """Demande acceptée : email + notification interne + poussée au mentoré."""
    offre = demande.offer
    mentee = demande.mentee
    domaine = offre.field
    nom_mentor = offre.mentor.get_full_name() or offre.mentor.username
    message = f'Votre demande de mentorat en « {domaine} » a été acceptée.'
    _notifie(mentee, 'Mentorat accepté 🎉', message)
    _email(mentee.email, 'Votre demande de mentorat a été acceptée',
           'mentorat_accepte',
           {'prenom': mentee.first_name or '', 'mentor': nom_mentor,
            'domaine': domaine})
    _poussee([mentee], 'Mentorat accepté 🎉', message, '/mentorat')


def apres_mentorat_decline(demande):
    """Demande refusée : email + notification interne + poussée au mentoré."""
    offre = demande.offer
    mentee = demande.mentee
    domaine = offre.field
    nom_mentor = offre.mentor.get_full_name() or offre.mentor.username
    message = f'Votre demande de mentorat en « {domaine} » a été déclinée.'
    _notifie(mentee, 'Mentorat décliné', message)
    _email(mentee.email, 'Votre demande de mentorat n\'a pas été retenue',
           'mentorat_decline',
           {'prenom': mentee.first_name or '', 'mentor': nom_mentor,
            'domaine': domaine})
    _poussee([mentee], 'Mentorat décliné', message, '/mentorat')


def apres_paiement_confirme(*, utilisateur, montant, projet, reference,
                            email=None):
    """Contribution confirmée : notification du donateur + reçu + alerte admin."""
    montant_txt = str(montant)
    detail_projet = f' au projet "{projet}"' if projet else ''

    # 1. Le donateur : notification interne (comportement historique conserve).
    if utilisateur:
        try:
            from .models import Notification
            Notification.objects.create(
                user=utilisateur,
                title='Paiement confirmé ✅',
                message=f'Votre contribution de {montant_txt} FCFA'
                        + detail_projet
                        + ' a été confirmée. Merci !',
                link='/projets',
            )
        except Exception:
            logger.exception('Notification donateur impossible.')

    # 2. Reçu par email (compte connecté, sinon l'adresse saisie du donateur).
    _email(
        (utilisateur.email if utilisateur else None) or email,
        f'Reçu de votre contribution — {montant_txt} FCFA',
        'contribution_recue',
        {
            'prenom': (utilisateur.first_name if utilisateur else '') or '',
            'montant': montant_txt,
            'projet': projet or '',
            'reference': reference or '',
        },
    )

    # 3. Les administrateurs : notification interne + poussée web.
    nom = ((utilisateur.get_full_name() or utilisateur.username)
           if utilisateur else 'Un donateur')
    message = (f'{nom} a confirmé une contribution de {montant_txt} FCFA'
               + detail_projet + f' (réf. {reference}).')
    notifier_admins('Nouveau paiement confirmé 💰', message, '/admin/contributions')
    cibles = list(_admins())
    if utilisateur:
        cibles.append(utilisateur)
    _poussee(cibles, 'Nouveau paiement confirmé 💰', message,
             '/admin/contributions')
