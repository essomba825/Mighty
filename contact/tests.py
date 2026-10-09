from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import ContactInfo, ContactMessage


class ContactInfoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_get(self):
        res = self.client.get(reverse('contact'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['email'], 'contact@megamightysixers.org')
        self.assertEqual(data['phone'], '+237 600 00 00 00')
        self.assertEqual(data['address']['fr'], 'Cameroun')
        self.assertEqual(data['address']['en'], 'Cameroon')
        self.assertEqual(data['hours']['en'], 'Monday to Saturday, 9 am — 5 pm')
        self.assertIn('facebook', {s['key'] for s in data['social']})
        self.assertIn('whatsapp', {s['key'] for s in data['social']})

    def test_create_singleton_if_missing(self):
        ContactInfo.objects.all().delete()
        res = self.client.get(reverse('contact'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ContactInfo.objects.count(), 1)

    def test_empty_social_omitted(self):
        info = ContactInfo.load()
        info.facebook = ''
        info.twitter = ''
        info.save()
        data = self.client.get(reverse('contact')).json()
        cles = {s['key'] for s in data['social']}
        self.assertNotIn('facebook', cles)
        self.assertNotIn('twitter', cles)


class ContactMessageTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_post_creates_message(self):
        res = self.client.post(reverse('contact'), {
            'name': 'Marie', 'email': 'marie@exemple.cm',
            'subject': 'Don', 'message': 'Bonjour, une question sur le don.',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.first()
        self.assertEqual(msg.name, 'Marie')

    def test_post_requires_name_email_message(self):
        res = self.client.post(reverse('contact'), {'name': ''}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ContactMessage.objects.count(), 0)