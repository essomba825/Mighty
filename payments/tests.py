import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from donations.models import Contribution
from notifications.models import Notification
from payments.models import Payment, PaymentRequest
from projects.models import Project

User = get_user_model()


def cree_projet():
    return Project.objects.create(
        title='Bibliothèque du lycée',
        description='Rénovation',
        objective='5000 livres',
        budget=2000000,
        status='active',
    )


class ReferenceConfigTest(TestCase):
    """La référence de paiement et la config marchand sont serveur-side."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='p0', email='p0@test.local',
                                             password='MotDePasse123!')

    def test_reference_generee_sans_connexion(self):
        r = self.client.get('/api/payments/requests/reference/')
        self.assertEqual(r.status_code, 200)
        self.assertRegex(r.json()['reference'], r'^MMS-[0-9A-F]{12}$')

    def test_config_retourne_les_codes_marchands(self):
        r = self.client.get('/api/payments/requests/config/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('beneficiary', data)
        self.assertIn('mtn_momo', data) and self.assertIn('orange_money', data)
        self.assertEqual(data['daily_limit'], 3)


class FluxPaiementTest(TestCase):
    """Flux SaveNow : limite journalière, demande, vérification par code."""

    def setUp(self):
        self.user = User.objects.create_user(username='p1', email='p1@test.local',
                                             password='MotDePasse123!')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.project = cree_projet()

    def payload(self, **overrides):
        data = {
            'payment_ref': 'MMS-TEST1234',
            'project': self.project.id,
            'donor_name': 'Jean Test',
            'donor_email': 'jean@test.local',
            'amount': 1000,
            'phone_number': '+237690000000',
            'provider': 'mtn_momo',
        }
        data.update(overrides)
        return data

    def test_creation_et_verification_completes(self):
        r = self.client.post('/api/payments/requests/', self.payload(), format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()['valid'])
        self.assertEqual(r.json()['code'], 'request_created')
        pr_id = r.json()['payment_request_id']

        demande = PaymentRequest.objects.get(pk=pr_id)
        self.assertEqual(demande.status, PaymentRequest.RequestStatus.INITIATED)
        self.assertEqual(demande.phone_number, '690000000')
        self.assertEqual(demande.contribution.status, Contribution.Status.PENDING)

        # Code trop court -> refusé
        r2 = self.client.post(f'/api/payments/requests/{pr_id}/verify/',
                              {'transaction_code': '12'}, format='json')
        self.assertEqual(r2.status_code, 400)
        self.assertFalse(r2.json()['valid'])

        # Bon code -> vérifié, contribution confirmée, Payment + notification
        r3 = self.client.post(f'/api/payments/requests/{pr_id}/verify/',
                              {'transaction_code': 'TX-ABCD1234'}, format='json')
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.json()['valid'])
        self.assertEqual(r3.json()['code'], 'verified')

        demande.refresh_from_db()
        self.assertEqual(demande.status, PaymentRequest.RequestStatus.VERIFIED)
        self.assertIsNotNone(demande.verified_at)
        self.assertEqual(demande.transaction_code, 'TX-ABCD1234')
        self.assertEqual(demande.contribution.status, Contribution.Status.CONFIRMED)
        self.assertTrue(hasattr(demande.contribution, 'payment'))
        self.assertEqual(demande.contribution.payment.status, Payment.Status.SUCCESS)
        self.assertTrue(Notification.objects.filter(user=self.user).exists())

        # Re-vérification idempotente
        r4 = self.client.post(f'/api/payments/requests/{pr_id}/verify/',
                              {'transaction_code': 'TX-ABCD1234'}, format='json')
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()['code'], 'already_verified')

    def test_validations_demandeur(self):
        cas = [
            ({'amount': 100}, 'invalid_amount'),
            ({'amount': 'abc'}, 'invalid_amount'),
            ({'phone_number': '61234'}, 'invalid_phone'),
            ({'phone_number': '512345678'}, 'invalid_phone'),
            ({'donor_email': 'pas-un-email'}, 'donor_email_invalid'),
            ({'provider': 'noodle'}, 'invalid_operator'),
            ({'project': None}, 'project_missing'),
        ]
        for overrides, code_attendu in cas:
            r = self.client.post('/api/payments/requests/',
                                 self.payload(**overrides), format='json')
            self.assertEqual(r.status_code, 400, (overrides, r.json()))
            self.assertFalse(r.json()['valid'])
            self.assertEqual(r.json()['text'], code_attendu,
                             (overrides, r.json()))
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_reference_deja_utilisee(self):
        self.client.post('/api/payments/requests/', self.payload(), format='json')
        r = self.client.post('/api/payments/requests/', self.payload(amount=2000), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['text'], 'payment_ref_used')

    def test_creation_sans_payment_ref_generee_par_le_serveur(self):
        payload = self.payload()
        payload.pop('payment_ref')

        r = self.client.post('/api/payments/requests/', payload, format='json')

        self.assertEqual(r.status_code, 201, r.json())
        self.assertTrue(r.json()['valid'])
        self.assertRegex(r.json()['reference'], r'^MMS-[0-9A-F]{12}$')
        self.assertEqual(PaymentRequest.objects.count(), 1)
        self.assertEqual(PaymentRequest.objects.get(pk=r.json()['payment_request_id']).payment_ref,
                         r.json()['reference'])

    def test_limite_journaliere_de_trois_demandes(self):
        for i in range(3):
            r = self.client.post('/api/payments/requests/',
                                 self.payload(payment_ref=f'MMS-TEST{i}',
                                              amount=1000 + i),
                                 format='json')
            self.assertEqual(r.status_code, 201, r.json())

        # Projet au complet : la quatrième dans la même journée est refusée
        r = self.client.post('/api/payments/requests/',
                             self.payload(payment_ref='MMS-TESTX', amount=5000),
                             format='json')
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()['text'], 'limit_reached')

        # Le compteur /total/ reflète la limite
        total = self.client.get(f'/api/payments/requests/total/?project={self.project.id}')
        self.assertEqual(total.json()['total_requests'], 3)
        self.assertEqual(total.json()['limit'], 3)

    def test_les_demandes_ouvertes_ne_comptent_pas(self):
        PaymentRequest.objects.create(payment_ref='MMS-OPEN-1', project=self.project,
                                      user=self.user, phone_number='690000000',
                                      amount=500, status=PaymentRequest.RequestStatus.OPENED)
        total = self.client.get(f'/api/payments/requests/total/?project={self.project.id}')
        self.assertEqual(total.json()['total_requests'], 0)

    def test_total_anonyme_par_telephone(self):
        anon = APIClient()
        # Une demande initiée pour un autre compte sur le même numéro
        autre = User.objects.create_user(username='p2', email='p2@test.local', password='x')
        self.client_autre = APIClient()
        self.client_autre.force_authenticate(autre)
        self.client_autre.post('/api/payments/requests/',
                               self.payload(payment_ref='MMS-ANON-9'), format='json')

        total = anon.get('/api/payments/requests/total/?phone=690000000')
        self.assertEqual(total.status_code, 200)
        self.assertEqual(total.json()['total_requests'], 1)

    def test_verification_refusee_sans_authentification(self):
        r = self.client.post('/api/payments/requests/', self.payload(), format='json')
        pr_id = r.json()['payment_request_id']
        anon = APIClient()
        r2 = anon.post(f'/api/payments/requests/{pr_id}/verify/',
                       {'transaction_code': 'ABCD1234'}, format='json')
        self.assertEqual(r2.status_code, 401 or 403)

    def test_paiement_compat_creation_directe(self):
        """L'ancien POST /api/payments/ reste fonctionnel (smoke_test)."""
        contrib = Contribution.objects.create(project=self.project, donor=self.user,
                                              donor_name='Jean', donor_email='jean@test.local',
                                              amount=1000, method='mtn_momo')
        r = self.client.post('/api/payments/', {
            'contribution': contrib.id, 'provider': 'mtn_momo',
            'phone_number': '690000000'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['status'], 'success')
        contrib.refresh_from_db()
        self.assertEqual(contrib.status, 'confirmed')


class CyclePrimaireTest(TestCase):
    """Le champ phone_number du PaymentRequest stocke le numéro normalisé."""

    def test_normalisation_des_trois_ecritures(self):
        for i, (brut, attendu) in enumerate([
                ('690000000', '690000000'),
                ('+237 690 000 000', '690000000'),
                ('237690000000', '690000000')]):
            user = User.objects.create_user(username=f'u{i}',
                                            email=f'u{i}@test.local',
                                            password='x')
            client = APIClient()
            client.force_authenticate(user)
            projet = cree_projet()
            cle = re.sub(r'\D', '', brut)
            r = client.post('/api/payments/requests/', {
                'payment_ref': f'MMS-NORM-{i}',
                'project': projet.id, 'donor_name': 'N', 'donor_email': 'n@test.local',
                'amount': 500, 'phone_number': brut, 'provider': 'orange_money'},
                format='json')
            self.assertEqual(r.status_code, 201, r.json())
            self.assertEqual(PaymentRequest.objects.get(pk=r.json()['payment_request_id'])
                             .phone_number, attendu)