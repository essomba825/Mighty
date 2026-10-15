# Cree la structure du module GCE Advanced Level Biologie (idempotent).
# Usage : ..\venv\Scripts\python.exe manage.py shell -c "exec(open('seed_biology_al.py',encoding='utf-8').read())"
from education.models import Subject, Chapter, Lesson

SUBJECT_ID = 4

CHAPTERS = {
    'cells': dict(order=1,
                  title='Cells and Biological Molecules',
                  title_fr='La cellule et les molecules biologiques'),
    'genetics': dict(order=2,
                     title='Genetics and Inheritance',
                     title_fr='Genetique et heredite'),
}

# chapter_key -> liste de lecons (order, title, title_fr, summary, summary_fr, objectives, objectives_fr)
LESSONS = [
    ('cells', 1, 'Cells and Cell Structure', 'La cellule et sa structure',
     'The cell as the unit of life: organelles, prokaryote versus eukaryote, '
     'and how each structure serves its function.',
     'La cellule comme unite du vivant : les organites, procaryote contre '
     'eucaryote, et comment chaque structure sert sa fonction.',
     ['Describe the structure and function of the main cell organelles',
      'Compare prokaryotic and eukaryotic cells',
      'Explain how cell structure relates to function'],
     ['Decrire la structure et la fonction des principaux organites',
      'Comparer les cellules procaryotes et eucaryotes',
      'Expliquer le lien entre structure et fonction de la cellule']),
    ('cells', 2, 'Biological Molecules', 'Les molecules biologiques',
     'Carbohydrates, proteins, lipids and nucleic acids: their building '
     'blocks, their bonds and their roles in the cell.',
     'Glucides, proteines, lipides et acides nucleiques : leurs elements de '
     'base, leurs liaisons et leurs roles dans la cellule.',
     ['Identify the four main classes of biological molecules',
      'Name the monomers and polymers of each class',
      'Relate the structure of each class to its role'],
     ['Identifier les quatre grandes classes de molecules biologiques',
      'Nommer les monomeres et polymeres de chaque classe',
      'Relier la structure de chaque classe a son role']),
    ('cells', 3, 'Enzymes', 'Les enzymes',
     'Biological catalysts: active site and specificity, and the factors '
     'that change the rate of an enzyme-controlled reaction.',
     'Les catalyseurs biologiques : site actif et specificite, et les '
     'facteurs qui modifient la vitesse d une reaction enzymatique.',
     ['Explain how enzymes speed up reactions',
      'Describe the lock-and-key model of enzyme action',
      'Explain the effect of temperature and pH on enzyme activity'],
     ['Expliquer comment les enzymes accelerent les reactions',
      'Decrire le modele cle-serrure de l action enzymatique',
      'Expliquer l effet de la temperature et du pH sur l activite']),
    ('cells', 4, 'Transport Across Membranes',
     'Le transport a travers les membranes',
     'Diffusion, osmosis and active transport: how substances cross the '
     'partially permeable cell membrane.',
     'Diffusion, osmose et transport actif : comment les substances '
     'traversent la membrane cellulaire semi-permeable.',
     ['Describe the structure of the cell membrane',
      'Explain diffusion and osmosis in cells',
      'Contrast passive transport and active transport'],
     ['Decrire la structure de la membrane cellulaire',
      'Expliquer la diffusion et l osmose dans les cellules',
      'Opposer transport passif et transport actif']),
    ('genetics', 1, 'Cell Division: Mitosis and Meiosis',
     'La division cellulaire : mitose et meiose',
     'How cells divide: mitosis for growth and repair, meiosis for gametes '
     'and genetic variation.',
     'Comment les cellules se divisent : la mitose pour la croissance et la '
     'reparation, la meiose pour les gametes et la variation genetique.',
     ['Describe the stages of mitosis',
      'Explain how meiosis produces gametes and variation',
      'Compare mitosis and meiosis'],
     ['Decrire les etapes de la mitose',
      'Expliquer comment la meiose produit les gametes et la variation',
      'Comparer mitose et meiose']),
    ('genetics', 2, 'DNA and Protein Synthesis',
     'L ADN et la synthese des proteines',
     'The structure of DNA, semi-conservative replication, and how the code '
     'is read by transcription and translation.',
     'La structure de l ADN, la replication semi-conservative, et la lecture '
     'du code par transcription et traduction.',
     ['Describe the structure of DNA',
      'Explain semi-conservative replication',
      'Outline transcription and translation'],
     ['Decrire la structure de l ADN',
      'Expliquer la replication semi-conservative',
      'Resumer la transcription et la traduction']),
]

subject = Subject.objects.get(pk=SUBJECT_ID)

chapters = {}
for key, meta in CHAPTERS.items():
    chapter, _ = Chapter.objects.get_or_create(
        subject=subject, order=meta['order'],
        defaults={'title': meta['title'], 'title_fr': meta['title_fr']})
    chapter.title = meta['title']
    chapter.title_fr = meta['title_fr']
    chapter.save(update_fields=['title', 'title_fr'])
    chapters[key] = chapter

created = []
for key, order, title, title_fr, summary, summary_fr, obj, obj_fr in LESSONS:
    lesson, is_new = Lesson.objects.get_or_create(
        chapter=chapters[key], title=title,
        defaults=dict(order=order, title_fr=title_fr, summary=summary,
                      summary_fr=summary_fr, objectives=obj,
                      objectives_fr=obj_fr, estimated_minutes=30))
    lesson.order = order
    lesson.title_fr = title_fr
    lesson.summary = summary
    lesson.summary_fr = summary_fr
    lesson.objectives = obj
    lesson.objectives_fr = obj_fr
    lesson.estimated_minutes = 30
    lesson.save()
    if is_new:
        created.append(lesson.id)

# Mendelian Genetics (14) rejoint le chapitre genetique.
mendel = Lesson.objects.filter(pk=14).first()
if mendel:
    mendel.chapter = chapters['genetics']
    mendel.order = 3
    mendel.estimated_minutes = max(mendel.estimated_minutes, 30)
    mendel.save(update_fields=['chapter', 'order', 'estimated_minutes'])

print('Chapitres :', {k: v.id for k, v in chapters.items()})
print('Nouvelles lecons creees :', created)
for key in ('cells', 'genetics'):
    print(f'-- {chapters[key].title}')
    for l in chapters[key].lessons.order_by('order'):
        print(f'   id={l.id} order={l.order} {l.title!r} status={l.status}')
