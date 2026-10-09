"""Données de test réalistes pour Mega Mighty Sixers."""
import django, os
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from news.models import NewsArticle
from events.models import Event
from projects.models import Project
from donations.models import Contribution, PartnershipRequest
from education.models import Subject, Chapter, Lesson, Quiz, Question, Choice
from alumni.models import AlumniProfile

User = get_user_model()
now = timezone.now()


def get_admin():
    u = User.objects.filter(is_superuser=True).first()
    if not u:
        u = User.objects.create_superuser('admin', 'admin@mightysixers.org', 'Admin123!')
        u.role = 'admin'; u.status = 'active'; u.save()
    return u


admin = get_admin()

# ---------- Membres ----------
membres = [
    ('nguepi.jean', 'nguepi@mightysixers.org', 'Jean', 'Nguepi', 2005, "Ingénieur génie civil", 'SOGEA SATOM', 'Douala'),
    ('mbarga.claire', 'mbarga@mightysixers.org', 'Claire', 'Mbarga', 2012, "Médecin généraliste", 'Hôpital Laquintinie', 'Douala'),
    ('tchoupo.alain', 'tchoupo@mightysixers.org', 'Alain', 'Tchoupo', 2000, "Professeur de mathématiques", 'Collège Bilingue', 'Yaoundé'),
    ('fotso.sylvie', 'fotso@mightysixers.org', 'Sylvie', 'Fotso', 2015, "Entrepreneure", 'Fotso Digital', 'Bafoussam'),
    ('ekane.paul', 'ekane@mightysixers.org', 'Paul', 'Ekane', 1998, "Comptable expert", 'Cabinet Ekane & Associés', 'Limbé'),
]
for username, email, first, last, promo, prof, company, city in membres:
    u, created = User.objects.get_or_create(email=email, defaults=dict(
        username=username, first_name=first, last_name=last, role='alumni', status='active'))
    if created:
        u.set_password('Membre123!')
        u.save()
        AlumniProfile.objects.get_or_create(user=u, defaults=dict(
            graduation_year=promo, profession=prof, company=company, city=city,
            bio=f"Ancien élève promotion {promo}, {prof.lower()} basé(e) à {city}."))
print(f'Membres : {User.objects.filter(role="alumni").count()}')

# ---------- Actualités ----------
actus = [
    ("Grande réunion générale des anciens élèves : plus de 150 participants",
     "Samedi dernier, l'association Mega Mighty Sixers a tenu sa réunion générale annuelle. Plus de 150 anciens élèves, venus de toutes les promotions, se sont retrouvés dans la grande salle de l'école.\n\nAu programme : bilan des activités de l'année, présentation des projets 2026-2027, et election du nouveau bureau. L'ambiance était à la fois studieuse et festive, ponctuée par de nombreux témoignages émouvants."),
    ("Lancement de la campagne « Un livre, un élève »",
     "L'association lance officiellement sa campagne de collecte de livres scolaires pour la bibliothèque de l'école.\n\nObjectif : 5 000 ouvrages collectés d'ici la fin de l'année scolaire. Chaque membre est invité à faire don de manuels en bon état ou à contribuer financièrement via la page Projets."),
    ("Nos élèves brillent au GCE 2026 : 94% de réussite",
     "Félicitations à nos élèves ! Le taux de réussite au GCE Ordinary et Advanced Level atteint 94% cette année, en hausse de 7 points.\n\nCe résultat exceptionnel doit beaucoup aux séances de préparation organisées par les anciens élèves bénévoles, et à la plateforme de cours en ligne."),
    ("Journée portes ouvertes : les anciens racontent leurs métiers",
     "Une vingtaine d'anciens élèves sont venus présenter leurs parcours professionnels aux élèves de Terminale : médecine, ingénierie, entrepreneuriat, fonction publique...\n\nDe précieux échanges qui aident les plus jeunes à construire leur projet d'orientation."),
]
for title, content in actus:
    NewsArticle.objects.get_or_create(title=title, defaults=dict(
        content=content, author=admin, published=True, published_at=now - timedelta(days=len(actus))))
print(f'Actualités : {NewsArticle.objects.count()}')

# ---------- Événements ----------
events = [
    ("Gala annuel des Mega Mighty Sixers", "Soirée de gala de fin d'année : dîner, remise des prix d'excellence et bal. Tenue de soirée exigée.",
     now + timedelta(days=30, hours=15), "Salle des fêtes de Bonanjo, Douala"),
    ("Séance de préparation au GCE — Mathématiques", "Révision intensive des probabilités et statistiques avec les professeurs bénévoles de l'association.",
     now + timedelta(days=7, hours=6), "Salle informatique de l'école"),
    ("Journée de salubrité à l'école", "Grand nettoyage et embellissement du campus : peinture des classes, entretien du terrain de sport.",
     now + timedelta(days=14, hours=3), "Campus de l'école"),
    ("Rencontre des promotions 1995-2005", "Retrouvailles réservées aux anciennes promotions : photos d'époque, repas partagé et anecdotes.",
     now + timedelta(days=45, hours=12), "Restaurant Le Panoramique, Yaoundé"),
]
for title, desc, date, lieu in events:
    Event.objects.get_or_create(title=title, defaults=dict(
        description=desc, date=date, location=lieu, organizer=admin, is_public=True))
print(f'Événements : {Event.objects.count()}')

# ---------- Projets ----------
projets = [
    ("School Library Renewal", "Upgrade the school library with new shelves, a digital reading corner, and climate control.",
     "Give students a proper study space: 5,000 books, 20 seats, and 5 computers.",
     2000000, 'active'),
    ("Excellence Scholarships 2027", "Fund the studies of the 10 top students from low-income families.",
     "Cover tuition, school supplies, and uniforms for the entire academic year.",
     3500000, 'active'),
    ("Science Laboratory Upgrade", "Equip the physics and chemistry lab with modern teaching materials.",
     "Provide microscopes, experiment kits, and chemistry supplies for hands-on practical lessons.",
     1500000, 'active'),
    ("Basketball Court Refurbishment", "Resurface the court and install new equipment.",
     "Create a standards-compliant court for inter-school competitions.",
     900000, 'funded'),
]
for title, desc, obj, budget, status in projets:
    p, _ = Project.objects.get_or_create(title=title, defaults=dict(
        description=desc, objective=obj, budget=budget, status=status, created_by=admin))
    # Contributions confirmées
    if status in ('active', 'funded') and not p.contributions.exists():
        montants = [100000, 50000, 200000, 25000] if status == 'active' else [900000]
        for i, m in enumerate(montants):
            Contribution.objects.create(
                project=p, donor_name=f'Donateur Test {i+1}', donor_email=f'don{i+1}@test.cm',
                amount=m, method='mtn_momo', status='confirmed')
print(f'Projets : {Project.objects.count()}')

# ---------- Partenariats ----------
PartnershipRequest.objects.get_or_create(
    organization='MTN Cameroon Fondation', contact_name='Mme Ngo Bassa',
    defaults=dict(email='fondation@mtn.cm', phone='655 00 00 00', partner_type='company',
                  message="Nous souhaitons sponsoriser la rénovation de la bibliothèque dans le cadre de notre programme éducation."))

# ---------- Éducation ----------
maths_ol, _ = Subject.objects.get_or_create(name='Mathématiques', level='ol', defaults={'description': 'Algèbre, géométrie et probabilités pour le GCE Ordinary Level.'})
phys_ol, _ = Subject.objects.get_or_create(name='Physique', level='ol', defaults={'description': 'Mécanique, électricité et optique.'})
maths_al, _ = Subject.objects.get_or_create(name='Mathématiques', level='al', defaults={'description': 'Analyse, suites et intégration pour le Advanced Level.'})
bio_al, _ = Subject.objects.get_or_create(name='Biologie', level='al', defaults={'description': 'Génétique, écologie et physiologie.'})

cours = [
    (maths_ol, "Les fractions et nombres rationnels", 1, "Une fraction représente une partie d'un tout.\n\nDéfinition : a/b où b ≠ 0.\n\nOpérations : addition, soustraction, multiplication et division de fractions.\n\nExemple : 1/2 + 1/3 = 3/6 + 2/6 = 5/6\n\nDans ce chapitre, tu apprendras à simplifier des fractions, trouver un dénominateur commun et résoudre des problèmes concrets.", False),
    (maths_ol, "Les équations du premier degré", 2, "Une équation du premier degré à une inconnue s'écrit ax + b = c.\n\nMéthode de résolution :\n1. Isoler les termes en x à gauche\n2. Regrouper les constantes à droite\n3. Diviser par le coefficient de x\n\nExemple : 3x + 5 = 14 → 3x = 9 → x = 3", False),
    (maths_ol, "Sujet GCE OL 2024 — Mathématiques (corrigé)", 3, "Sujet complet de l'épreuve de mathématiques, session 2024, avec le corrigé détaillé question par question.\n\nConseils de méthode : l'intégralité du sujet en 2h30, gestion du temps, points fréquemment piégés.", True),
    (phys_ol, "Mouvement et vitesse", 1, "La vitesse moyenne d'un mobile est v = d/t.\n\nUnités : m/s ou km/h (1 m/s = 3,6 km/h).\n\nMouvement uniforme et uniformément varié : équations et graphes vitesse-temps.", False),
    (maths_al, "Les suites arithmétiques et géométriques", 1, "Suite arithmétique : un+1 = un + r.\nTerme général : un = u1 + (n-1)r.\nSomme : Sn = n/2 × (u1 + un).\n\nSuite géométrique : un+1 = un × q.\nTerme général : un = u1 × q^(n-1).", False),
    (bio_al, "La génétique mendélienne", 1, "Les lois de Mendel régissent la transmission des caractères héréditaires.\n\n1ère loi : uniformité des hybrides de 1ère génération.\n2ème loi : disjonction des caractères en 2ème génération (3/4 - 1/4).", False),
]
for subject, title, chap, content, exam in cours:
    chapter, _ = Chapter.objects.get_or_create(subject=subject, order=chap,
                                               defaults=dict(title=f'Chapter {chap}'))
    lesson, _ = Lesson.objects.get_or_create(chapter=chapter, title=title, defaults=dict(
        order=1, kind='exam_paper' if exam else 'lesson', content=content,
        teacher=admin, status='published'))

c1 = Lesson.objects.filter(chapter__subject=maths_ol, chapter__order=1).first()
if c1 and not c1.quizzes.exists():
    quiz = Quiz.objects.create(lesson=c1, title="Quiz : les fractions", pass_score=60)
    q1 = Question.objects.create(quiz=quiz, text="1/2 + 1/4 = ?", order=1)
    Choice.objects.create(question=q1, text="3/4", is_correct=True)
    Choice.objects.create(question=q1, text="2/6", is_correct=False)
    Choice.objects.create(question=q1, text="1/6", is_correct=False)
    q2 = Question.objects.create(quiz=quiz, text="La forme simplifiée de 12/18 est :", order=2)
    Choice.objects.create(question=q2, text="2/3", is_correct=True)
    Choice.objects.create(question=q2, text="6/9", is_correct=False)
    Choice.objects.create(question=q2, text="4/6", is_correct=False)
print(f'Leçons publiées : {Lesson.objects.filter(status="published").count()}')

print('\n✅ Données de test créées avec succès !')
