"""Cree les matieres du GCE Science Hub si elles manquent.

Regles :
- idempotent : le relancer ne duplique rien ni ne renomme rien ;
- on cree la MATIERE seule, pas de chapitres bidons ni de lecons vides, sinon
  l'eleve tombe sur une page blanche ;
- on ne touche jamais aux matieres existantes (les doublons mathematiques-ol
  et mathematiques-al restent tels quels).
"""
from django.core.management.base import BaseCommand

from education.models import Subject

# Sujets officiels du GCE Science Hub :
#   - Maths (deja present : mathematiques-ol, mathematiques-al, mathematics-ol)
#   - Biologie (deja : biologie-al) -> ajout de l'OL
#   - Chimie (absente) -> ajout OL et AL
#   - Physique (deja : physique-ol) -> ajout de l'AL
GCE_SPRING = [
    ('chemistry-ol', 'ol', 'Chemistry', 'GCE Ordinary Level Chemistry: matter, atomic structure, chemical reactions, acids, bases and salts.', 'mdi-atom', '#2e7d6e',
     'Wikimedia Commons, chemistry lab flasks'),
    ('chemistry-al', 'al', 'Chemistry', 'GCE Advanced Level Chemistry: organic, inorganic and physical chemistry with quantitative analysis.', 'mdi-atom', '#2e7d6e',
     'Wikimedia Commons, chemistry lab flasks'),
    ('physics-al', 'al', 'Physics', 'GCE Advanced Level Physics: mechanics, electricity, waves and modern physics.', 'mdi-speedometer', '#1565c0',
     'Wikimedia Commons, laboratory optics'),
    ('biology-ol', 'ol', 'Biology', 'GCE Ordinary Level Biology: cell, nutrition, reproduction, ecology and classification.', 'mdi-lungs', '#33691e',
     'Wikimedia Commons, microscope'),
]


class Command(BaseCommand):
    help = "Cree les matieres du GCE Science Hub manquantes (idempotent)"

    def handle(self, *args, **options):
        created, existing = [], []
        for slug, level, name, desc, icon, color, img_hint in GCE_SPRING:
            if Subject.objects.filter(slug=slug).exists():
                existing.append(slug)
                continue
            if Subject.objects.filter(level=level, name=name).exists():
                self.stdout.write(self.style.WARNING(
                    f'  Saute {slug} : une matiere {name!r} niveau {level!r} existe '
                    f'deja sous un autre slug'))
                continue
            subject = Subject.objects.create(
                name=name, level=level, description=desc,
                icon='mdi-book-outline', color=color)
            # Le slug genere est dérivé du nom : on le force pour coller aux
            # reperes du sujet (chemistry-ol plutot que chemistry-ol-2 logique).
            subject.slug = slug
            subject.save()
            created.append(slug)
            self.stdout.write(self.style.SUCCESS(f'  Cree : {slug} ({name}, {level})'))

        self.stdout.write(
            f'\nResultat : {len(created)} creee(s), {len(existing)} existante(s).')
        for slug in sorted(existing):
            self.stdout.write(f'  existait deja : {slug}')
