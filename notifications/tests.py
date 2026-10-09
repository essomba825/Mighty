"""Tests des trois canaux (email, notification admin, poussée web) pour les
trois événements : inscription, demande de mentorat, paiement confirmé."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from donations.models import Contribution
from mentorship.models import MentorshipOffer, MentorshipRequest
from notifications.models import Notification, PushSubscription
from payments.models import PaymentRequest
from projects.models import Project

User = get_user_model()


def actif(username, email, **kwargs):
    kwargs.setdefault('password', 'MotDePasse123!')
    kwargs.setdefault('status', 'active')
    return User.objects.create_user(username=username, email=email, **kwargs)


class InscriptionTest(TestCase):
    """Creation de compte : email de bienvenue + alerte des admins."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1', email='admin@test.local',
            password='x', is_staff=True)
        self.client = APIClient()

    def test_email_bienvenue_et_alerte_admin(self):
        r = self.client.post('/api/auth/register/', {
            'email': 'nouveau@test.local', 'username': 'nouveau',
            'password': 'MotDePasse123!', 'first_name': 'Jean',
            'last_name': 'Mbarga',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.json())

        # 1. Email de bienvenue envoye au futur membre.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('nouveau@test.local', mail.outbox[0].to)
        self.assertIn('validation', mail.outbox[0].subject.lower())

        # 2. Notification interne pour chaque admin.
        notif = Notification.objects.get(user=self.admin)
        self.assertIn('compte', notif.title.lower())
        self.assertEqual(notif.link, '/admin/membres')


class MentoratTest(TestCase):
    """Demande de mentorat : accusé au mentee + alerte admin."""

    def setUp(self):
        self.mentor = actif('mentor1', 'mentor@test.local')
        self.admin = User.objects.create_user(
            username='admin2', email='admin2@test.local',
            password='x', is_staff=True)
        self.mentee = actif('eleve1', 'eleve@test.local', first_name='Aline')
        self.offre = MentorshipOffer.objects.create(
            mentor=self.mentor, field='Ingénierie',
            description='Coaching carrière')
        self.client = APIClient()
        self.client.force_authenticate(self.mentee)

    def test_trois_canaux(self):
        r = self.client.post('/api/mentorship/requests/', {
            'offer': self.offre.id, 'message': 'Je souhaite être mentoré.',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.json())

        # 1. Email d'accusé de reception au mentee.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('eleve@test.local', mail.outbox[0].to)
        self.assertIn('Ingénierie', mail.outbox[0].body)

        # 2. Notification de l'historique au mentor, et celle des admins.
        self.assertTrue(Notification.objects.filter(user=self.mentor).exists())
        self.assertTrue(
            Notification.objects.filter(user=self.admin, link='/mentorat').exists())

        # 3. L'abonnement push du mentor recoit la poussée.
        abo = PushSubscription.objects.create(
            user=self.mentor, endpoint='https://push.test/abc',
            p256dh='cle', auth='auth')
        with mock.patch('pywebpush.webpush') as faux_push:
            from notifications.services import apres_demande_mentorat
            apres_demande_mentorat(MentorshipRequest.objects.first())
        self.assertEqual(faux_push.call_count, 1)
        info = faux_push.call_args.kwargs['subscription_info']
        self.assertEqual(info['endpoint'], abo.endpoint)
        # La charge utile contient le titre de l'alerte.
        self.assertIn('mentorat', faux_push.call_args.kwargs['data'].lower())

    def test_abonnement_mort_supprime(self):
        """Un endpoint 410 du service push est purge de la base."""
        abo = PushSubscription.objects.create(
            user=self.mentor, endpoint='https://push.test/perime',
            p256dh='cle', auth='auth')

        class Reponse:
            status_code = 410

        from pywebpush import WebPushException
        with mock.patch('pywebpush.webpush',
                        side_effect=WebPushException('gone', response=Reponse())):
            from notifications.push import envoyer_poussee
            envoyer_poussee([self.mentor], 'Test', 'Corps')
        self.assertFalse(PushSubscription.objects.filter(pk=abo.pk).exists())


class MentoratReponseTest(TestCase):
    """Acceptation / refus : le mentoré est notifié (email + in-app + push),
    sans doublon si l'action est répétée."""

    def setUp(self):
        self.mentor = actif('mentor3', 'mentor3@test.local', first_name='Aline')
        self.mentee = actif('eleve3', 'eleve3@test.local', first_name='Paul')
        self.offre = MentorshipOffer.objects.create(
            mentor=self.mentor, field='Médecine', description='Coaching')
        self.demande = MentorshipRequest.objects.create(
            offer=self.offre, mentee=self.mentee, message='Aide moi svp')
        self.client = APIClient()
        self.client.force_authenticate(self.mentor)

    def test_accept_notifie_le_mentore(self):
        r = self.client.post(f"/api/mentorship/requests/{self.demande.id}/accept/")
        self.assertEqual(r.status_code, 200, r.json())
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.status, 'accepted')

        # Email.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('eleve3@test.local', mail.outbox[0].to)
        self.assertIn('Médecine', mail.outbox[0].body)
        self.assertIn('accepté', mail.outbox[0].subject.lower())

        # Notification interne.
        self.assertTrue(Notification.objects.filter(
            user=self.mentee, title__contains='accepté').exists())

        # Poussée web vers le mentoré.
        abo = PushSubscription.objects.create(
            user=self.mentee, endpoint='https://push.test/accept',
            p256dh='cle', auth='auth')
        with mock.patch('pywebpush.webpush') as faux_push:
            from notifications.services import apres_mentorat_accepte
            apres_mentorat_accepte(self.demande)
        self.assertEqual(faux_push.call_count, 1)
        info = faux_push.call_args.kwargs['subscription_info']
        self.assertEqual(info['endpoint'], abo.endpoint)

    def test_accept_repetee_ne_double_pas(self):
        self.client.post(f"/api/mentorship/requests/{self.demande.id}/accept/")
        r2 = self.client.post(f"/api/mentorship/requests/{self.demande.id}/accept/")
        self.assertEqual(r2.status_code, 200, r2.json())
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.status, 'accepted')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notification.objects.filter(
            user=self.mentee, title__contains='accepté').count(), 1)

    def test_decline_notifie_le_mentore(self):
        r = self.client.post(f"/api/mentorship/requests/{self.demande.id}/decline/")
        self.assertEqual(r.status_code, 200, r.json())
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.status, 'declined')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('eleve3@test.local', mail.outbox[0].to)
        self.assertIn("n'a pas retenu", mail.outbox[0].body)
        self.assertIn('retenue', mail.outbox[0].subject.lower())
        self.assertTrue(Notification.objects.filter(
            user=self.mentee, title__contains='décliné').exists())

    def test_decline_repetee_ne_double_pas(self):
        self.client.post(f"/api/mentorship/requests/{self.demande.id}/decline/")
        r2 = self.client.post(f"/api/mentorship/requests/{self.demande.id}/decline/")
        self.assertEqual(r2.status_code, 200, r2.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notification.objects.filter(
            user=self.mentee, title__contains='décliné').count(), 1)


class PaiementTest(TestCase):
    """Paiement confirme : notif donateur + receipt email + alerte admin."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin3', email='admin3@test.local',
            password='x', is_staff=True)
        self.donneur = actif('don1', 'don@test.local', first_name='Paul')
        self.projet = Project.objects.create(
            title='Bibliothèque', description='Rénovation', objective='500 livres',
            budget=1000000, status='active')
        self.client = APIClient()
        self.client.force_authenticate(self.donneur)

    def test_trois_canaux(self):
        r = self.client.post('/api/payments/requests/', {
            'payment_ref': 'MMS-NOTIF-1', 'project': self.projet.id,
            'donor_name': 'Paul', 'donor_email': 'don@test.local',
            'amount': 2500, 'phone_number': '+237690000000',
            'provider': 'mtn_momo',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.json())
        r2 = self.client.post(
            f"/api/payments/requests/{r.json()['payment_request_id']}/verify/",
            {'transaction_code': 'TX-ABC1234'}, format='json')
        self.assertEqual(r2.status_code, 200, r2.json())

        # 1. Reçu par email au donateur.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('don@test.local', mail.outbox[0].to)
        self.assertIn('2500', mail.outbox[0].body)

        # 2. Notification du donateur (comportement historique conserve).
        self.assertTrue(Notification.objects.filter(user=self.donneur).exists())

        # 3. Alerte des admins (notification interne).
        self.assertTrue(Notification.objects.filter(
            user=self.admin, link='/admin/contributions').exists())

    def test_reverification_ne_double_pas(self):
        """already_verified ne renvoie pas un deuxieme reçu."""
        r = self.client.post('/api/payments/requests/', {
            'payment_ref': 'MMS-NOTIF-2', 'project': self.projet.id,
            'donor_name': 'Paul', 'donor_email': 'don@test.local',
            'amount': 1000, 'phone_number': '+237690000000',
            'provider': 'mtn_momo',
        }, format='json')
        pk = r.json()['payment_request_id']
        self.client.post(f'/api/payments/requests/{pk}/verify/',
                         {'transaction_code': 'TX-ABC1234'}, format='json')
        self.client.post(f'/api/payments/requests/{pk}/verify/',
                         {'transaction_code': 'TX-ABC1234'}, format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notification.objects.filter(
            user=self.donneur, title='Paiement confirmé ✅').count(), 1)


class PushEndpointsTest(TestCase):
    """Abonnement, compteur et configuration push."""

    def setUp(self):
        self.user = actif('push1', 'push@test.local')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_subscribe_compteur_unsubscribe(self):
        r = self.client.post('/api/notifications/push_subscribe/', {
            'endpoint': 'https://push.test/nouveau',
            'keys': {'p256dh': 'cle256', 'auth': 'cleauth'},
            'expirationTime': None,
        }, format='json')
        self.assertEqual(r.status_code, 200, r.json())
        abo = PushSubscription.objects.get(endpoint='https://push.test/nouveau')
        self.assertEqual(abo.user, self.user)

        # Meme endpoint -> un seul abonnement (update, pas de doublon).
        self.client.post('/api/notifications/push_subscribe/', {
            'endpoint': 'https://push.test/nouveau',
            'keys': {'p256dh': 'autre', 'auth': 'autre'},
        }, format='json')
        self.assertEqual(PushSubscription.objects.count(), 1)

        Notification.objects.create(user=self.user, title='T', message='m')
        r = self.client.get('/api/notifications/unread_count/')
        self.assertEqual(r.json()['unread_count'], 1)

        r = self.client.post('/api/notifications/push_unsubscribe/',
                             {'endpoint': 'https://push.test/nouveau'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_push_config_retourne_la_cle(self):
        r = self.client.get('/api/notifications/push_config/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('public_key', r.json())
        self.assertIn('enabled', r.json())

    def test_endpoints_soumis_authentification(self):
        anon = APIClient()
        self.assertEqual(
            anon.get('/api/notifications/unread_count/').status_code, 401)
        self.assertEqual(
            anon.post('/api/notifications/push_subscribe/', {}).status_code, 401)
