"""Attache des ressources pedagogiques (videos YouTube verifiees) aux lecons.

Recherche manuelle : chapitres 1 et 2 du programme Mathematics GCE OL.
Toutes les videos viennent de Khan Academy (plateforme educative gratuite).
Lancer : venv\\Scripts\\python.exe manage.py shell -c "exec(open('seed_resources.py', encoding='utf-8').read())"
"""
from education.models import Lesson, Resource

KHAN = {
    'source_name': 'Khan Academy',
    'license_note': 'Contenu educatif gratuit - Khan Academy (partage YouTube)',
}

# titre de lecon -> (video principale, [ressources (url, titre)])
LINKS = {
    'Types of Numbers and Prime Factors': (
        'https://www.youtube.com/watch?v=ZKKDTfHcsG0',
        [
            ('https://www.youtube.com/watch?v=mIStB5X4U8M', 'Prime numbers (Khan Academy)'),
            ('https://www.youtube.com/watch?v=5xe-6GPR_qQ', 'Finding factors and multiples (Khan Academy)'),
            ('https://www.youtube.com/watch?v=kSaUsBYCAms', 'HCF and LCM with prime factors (Khan Academy)'),
        ]),
    'Fractions, Decimals and Percentages': (
        'https://www.youtube.com/watch?v=-gB1y-PMWfs',
        [
            ('https://www.youtube.com/watch?v=Gn2pdkvdbGQ', 'Converting fractions to decimals (Khan Academy)'),
            ('https://www.youtube.com/watch?v=FaDtge_vkbg', 'Finding a percentage (Khan Academy)'),
            ('https://www.youtube.com/playlist?list=PLSQl0a2vh4HCQHWDXEKSnY3-cygkXGiyN',
             'Playlist : Fractions, decimals & percentages (Khan Academy)'),
        ]),
    'Ratio and Proportion': (
        'https://www.youtube.com/watch?v=WfqgFBGet7s',
        [
            ('https://www.youtube.com/watch?v=HpdMJaKaXXc', 'Introduction to ratios (Khan Academy)'),
            ('https://www.youtube.com/watch?v=p5nomPfUF9k', 'Simplifying rates and ratios (Khan Academy)'),
        ]),
    'Standard Form (Scientific Notation)': (
        'https://www.youtube.com/watch?v=trdbaV4TaAo',
        [
            ('https://www.youtube.com/watch?v=i6lfVUp5RW8', 'Scientific notation examples (Khan Academy)'),
        ]),
}

attached = 0
for title, (video_url, extra) in LINKS.items():
    lesson = Lesson.objects.filter(title=title).first()
    if not lesson:
        print(f'[??] Lecon introuvable : {title}')
        continue
    lesson.video_url = video_url
    lesson.save()
    for i, (url, label) in enumerate(extra, start=1):
        _, created = Resource.objects.get_or_create(
            lesson=lesson, url=url,
            defaults={'title': label, 'kind': 'video', 'order': i, **KHAN})
        attached += 1 if created else 0
    print(f'[OK] {title} : video principale + {len(extra)} ressources')

print(f'\n[TERMINE] {attached} ressources attachees')
