"""Smoke test Phase 1 : auth JWT, profil alumni, events, news, archives."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import json
from rest_framework.test import APIClient
from accounts.models import User

client = APIClient()

# Nettoyage des exécutions précédentes
User.objects.filter(email='jean@test.com').delete()

def check(name, resp, expected=(200, 201)):
    ok = resp.status_code in expected
    print(f"{'PASS' if ok else 'FAIL'} [{resp.status_code}] {name}")
    if not ok:
        print('   ->', resp.content[:300])
    return ok

# 1. Routes publiques
check('GET /api/news/ (public)', client.get('/api/news/'))
check('GET /api/events/ (public)', client.get('/api/events/'))
check('GET /api/archives/ (public)', client.get('/api/archives/'))

# 2. Inscription (statut pending)
r = client.post('/api/auth/register/', {
    'email': 'jean@test.com', 'username': 'jean', 'password': 'Passw0rd!x',
    'first_name': 'Jean', 'last_name': 'Test', 'role': 'alumni'
}, format='json')
check('POST /api/auth/register/', r)
user = User.objects.get(email='jean@test.com')
print('   -> statut créé:', user.status)
assert user.status == 'pending', 'Le compte doit être en attente de validation admin'

# 3. Validation admin + login
user.status = 'active'
user.save()
r = client.post('/api/auth/login/', {'identifier': 'jean@test.com', 'password': 'Passw0rd!x'}, format='json')
check('POST /api/auth/login/ (JWT)', r)
token = r.json()['access']
client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

# 4. Profil connecté
check('GET /api/auth/me/', client.get('/api/auth/me/'))

# 5. Création profil alumni
r = client.post('/api/alumni/profiles/', {'graduation_year': 2010, 'profession': 'Ingénieur',
                                          'city': 'Douala'}, format='json')
check('POST /api/alumni/profiles/', r)

# 6. Permissions : un membre ne peut pas créer un événement
check('POST /api/events/ refusé pour un membre', client.post('/api/events/', {
    'title': 'X', 'description': 'X', 'date': '2026-10-01T10:00:00Z', 'location': 'X'
}, format='json'), expected=(401, 403))

# --- Phase 2 : projets, contributions, partenariats, notifications ---
from projects.models import Project
from notifications.models import Notification

# 7. Admin crée un projet
admin = User.objects.get(email='admin@mightysixers.org')
project, _ = Project.objects.get_or_create(
    title='Bibliothèque du lycée', defaults={
        'description': 'Rénovation de la bibliothèque', 'objective': '5000 livres et 20 tables',
        'budget': 2000000, 'status': 'active', 'created_by': admin})

check('GET /api/projects/ (public)', client.get('/api/projects/'))

# 8. Contribution publique (sans compte)
anon = APIClient()
project.contributions.all().delete()  # idempotence entre exécutions
r = anon.post('/api/donations/contributions/', {
    'project': project.id, 'donor_name': 'Marie Don', 'donor_email': 'marie@don.com',
    'amount': 50000, 'method': 'mtn_momo'}, format='json')
check('POST /api/donations/contributions/ (public)', r)

# 9. Contribution confirmée -> montant collecté
contrib = project.contributions.first()
contrib.status = 'confirmed'
contrib.save()
r = anon.get(f'/api/projects/{project.id}/')
collected = r.json()['amount_collected']
check('GET projet avec montant collecté', r)
assert collected == 50000, f'Montant collecté incorrect: {collected}'
print(f'   -> collecté: {collected} FCFA / reste: {r.json()["funds_remaining"]} FCFA')

# 10. Demande de partenariat publique
r = anon.post('/api/donations/partnerships/', {
    'organization': 'Entreprise ABC', 'contact_name': 'M. Directeur',
    'email': 'contact@abc.com', 'partner_type': 'company', 'message': 'Nous souhaitons sponsoriser.'
}, format='json')
check('POST /api/donations/partnerships/ (public)', r)

# 11. Partenariats réservés aux admins
check('GET /api/donations/partnerships/ refusé pour un membre',
      client.get('/api/donations/partnerships/'), expected=(403,))

# 12. Notifications de l'utilisateur
Notification.objects.create(user=user, title='Bienvenue', message='Compte validé !')
check('GET /api/notifications/', client.get('/api/notifications/'))
notif_id = client.get('/api/notifications/').json()[0]['id']
check('POST mark_read', client.post(f'/api/notifications/{notif_id}/mark_read/'))

# --- Phase 3 : espace éducatif ---
from education.models import Subject, Chapter, Lesson, Quiz, Question, Choice

# 13. Catalogue public : matières + leçons publiées, sans compte
anon2 = APIClient()
check('GET /api/education/subjects/ public', anon2.get('/api/education/subjects/'))
check('GET /api/education/lessons/ public', anon2.get('/api/education/lessons/'))

# 14. Admin crée matière + chapitre + leçon publiée + quiz
subject, _ = Subject.objects.get_or_create(name='Mathématiques', level='ol')
chapter, _ = Chapter.objects.get_or_create(subject=subject, order=1,
                                           defaults={'title': 'Fractions'})
admin_client = APIClient()
admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {APIClient().post('/api/auth/login/', {'identifier': 'admin@mightysixers.org', 'password': 'Admin123!'}, format='json').json()['access']}")
r = admin_client.post('/api/education/lessons/', {
    'chapter': chapter.id, 'title': 'Chapitre 1 : Les fractions', 'order': 1,
    'content': 'Une fraction est...'}, format='json')
check('POST /api/education/lessons/ (admin, publiée direct)', r)
lesson_id = r.json()['id']
assert r.json()['status'] == 'published'

quiz, _ = Quiz.objects.get_or_create(lesson_id=lesson_id, title='Quiz fractions', defaults={'pass_score': 50})
question, _ = Question.objects.get_or_create(quiz=quiz, text='1/2 + 1/4 = ?', defaults={'order': 1})
good, _ = Choice.objects.get_or_create(question=question, text='3/4', defaults={'is_correct': True})
Choice.objects.get_or_create(question=question, text='2/6', defaults={'is_correct': False})

# 15. Enseignant crée une leçon -> en attente de validation
teacher = User.objects.get_or_create(email='prof@test.com', defaults={
    'username': 'prof', 'first_name': 'Prof', 'last_name': 'Test',
    'role': 'teacher', 'status': 'active'})[0]
teacher.set_password('Passw0rd!x'); teacher.save()
teacher_tok = APIClient().post('/api/auth/login/', {'identifier': 'prof@test.com', 'password': 'Passw0rd!x'}, format='json').json()['access']
teacher_client = APIClient(); teacher_client.credentials(HTTP_AUTHORIZATION=f'Bearer {teacher_tok}')
r = teacher_client.post('/api/education/lessons/', {
    'chapter': chapter.id, 'title': 'Chapitre 2 : Les pourcentages', 'order': 2,
    'content': 'Un pourcentage est...'}, format='json')
check('POST /api/education/lessons/ (enseignant -> pending)', r)
assert r.json()['status'] == 'pending'

# 16. Le catalogue public ne montre que les leçons publiées
r = anon2.get('/api/education/lessons/')
titles = [c['title'] for c in (r.json().get('results') if isinstance(r.json(), dict) else r.json())]
assert 'Chapitre 1 : Les fractions' in titles, titles
assert 'Chapitre 2 : Les pourcentages' not in titles, titles

# 16b. Le détail d'une leçon demande un compte
r = anon2.get(f'/api/education/lessons/{lesson_id}/')
check('GET leçon sans login -> 401', r, expected=(401,))
check('GET leçon connectée', client.get(f'/api/education/lessons/{lesson_id}/'))

# 16c. Progression : marquer la leçon terminée
check('POST lesson complete', client.post(f'/api/education/lessons/{lesson_id}/complete/'), expected=(201,))
r = client.get('/api/education/lessons/my_progress/')
check('GET my_progress', r)
assert any(item['lesson']['id'] == lesson_id for item in r.json()), r.json()

# 17. L'élève soumet le quiz -> score enregistré
r = client.post(f'/api/education/quizzes/{quiz.id}/submit/',
                {'answers': {str(question.id): good.id}}, format='json')
check('POST soumission quiz (1/1 = 100%, réussi)', r)
assert r.json()['score'] == 1 and r.json()['passed'] is True
print(f'   -> score: {r.json()["score"]}/{r.json()["total"]} ({r.json()["percentage"]}%)')

# 18. Suivi de progression
r = client.get('/api/education/results/')
check('GET /api/education/results/ (mes résultats)', r)

# --- Phase 4 : paiements, carte membre, mentorat, stats ---
from alumni.models import MemberCard, AlumniProfile
from mentorship.models import MentorshipOffer
from datetime import date, timedelta

# 19. Demande de paiement Mobile Money (flux SaveNow) puis vérification par code
Contribution = __import__('donations.models', fromlist=['Contribution']).Contribution
PaymentRequest = __import__('payments.models', fromlist=['PaymentRequest']).PaymentRequest
r = client.get('/api/payments/requests/reference/')
check('GET payment reference', r)
payment_ref = r.json()['reference']
r = client.post('/api/payments/requests/', {
    'payment_ref': payment_ref, 'project': project.id, 'donor_name': 'Jean Test',
    'donor_email': 'jean@test.com', 'amount': 25000, 'phone_number': '+237690000000',
    'provider': 'mtn_momo', 'message': 'Bravo pour le projet'}, format='json')
check('POST /api/payments/requests/ (demande initiée)', r)
assert r.json()['valid'] is True and r.json()['code'] == 'request_created', r.json()
pr_id = r.json()['payment_request_id']
print(f"   -> demande {payment_ref} initiée (id {pr_id})")

# Code de transaction trop court -> refus
r2 = client.post(f'/api/payments/requests/{pr_id}/verify/',
                 {'transaction_code': '12'}, format='json')
check('POST verify (code trop court -> 400)', r2, expected=(400,))

# Bon code -> contribution confirmée + notification
r = client.post(f'/api/payments/requests/{pr_id}/verify/',
                {'transaction_code': 'TX-CONF-1234'}, format='json')
check('POST verify (paiement confirmé)', r)
assert r.json()['valid'] is True, r.json()
demande = PaymentRequest.objects.get(pk=pr_id)
assert demande.status == 'verified' and demande.contribution.status == 'confirmed', \
    f"demande: {demande.status}, contribution: {demande.contribution.status}"
print(f"   -> paiement {demande.payment_ref} : contribution confirmée")
print(f"   -> demandes du jour : {client.get(f'/api/payments/requests/total/?project={project.id}').json()}")

# 19bis. Ancien POST /api/payments/ toujours compatible (partenaire déjà authentifié)
new_contrib = Contribution.objects.create(
    project=project, donor=user, donor_name='Jean Test', donor_email='jean@test.com',
    amount=25000, method='mtn_momo')
r = client.post('/api/payments/', {
    'contribution': new_contrib.id, 'provider': 'mtn_momo', 'phone_number': '690000000'
}, format='json')
check('POST /api/payments/ (compat directe)', r)
new_contrib.refresh_from_db()
assert r.json()['status'] == 'success' and new_contrib.status == 'confirmed', \
    f"paiement: {r.json()['status']}, contribution: {new_contrib.status}"
print(f"   -> paiement {r.json()['reference']} : contribution confirmée automatiquement")

# 20. Carte de membre numérique
profile = AlumniProfile.objects.get(user=user)
r = client.get('/api/alumni/profiles/my_card/')
check('GET my_card sans carte -> 404', r, expected=(404,))
MemberCard.objects.get_or_create(profile=profile, defaults={
    'card_number': 'MMS-2026-0001', 'valid_until': date.today() + timedelta(days=365)})
r = client.get('/api/alumni/profiles/my_card/')
check('GET my_card avec carte', r)
print(f"   -> carte {r.json()['card_number']} valide jusqu'au {r.json()['valid_until']}")

# 21. Mentorat : offre + demande + acceptation
r = client.post('/api/mentorship/offers/', {
    'field': 'Ingénierie', 'description': "Accompagnement des jeunes diplômés",
    'availability': 'Week-ends'}, format='json')
check('POST /api/mentorship/offers/', r)
offer = MentorshipOffer.objects.get(mentor=user)
r = teacher_client.post('/api/mentorship/requests/', {
    'offer': offer.id, 'message': 'Je cherche un mentor en génie civil.'}, format='json')
check('POST /api/mentorship/requests/', r)
request_id = r.json()['id']
r = client.post(f'/api/mentorship/requests/{request_id}/accept/')
check('POST accept (mentor accepte)', r)

# 22. Statistiques réservées aux admins
check('GET /api/stats/ refusé pour un membre', client.get('/api/stats/'), expected=(403,))
r = admin_client.get('/api/stats/')
check('GET /api/stats/ (admin)', r)
s = r.json()
print(f"   -> membres actifs: {s['members']['total']}, collecté: "
      f"{s['contributions']['total_amount']} FCFA, cours publiés: {s['education']['courses_published']}")

print('\n--- Smoke test terminé ---')

