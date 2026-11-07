# Cree la structure du module GCE Advanced Level Mathematiques (idempotent).
# Usage : ..\venv\Scripts\python.exe manage.py shell -c "exec(open('seed_maths_al.py',encoding='utf-8').read())"
from education.models import Subject, Chapter, Lesson

SUBJECT_ID = 3

CHAPTERS = {
    'sequences': dict(order=1,
                      title='Sequences and Series',
                      title_fr='Suites et series'),
    'algebra': dict(order=2,
                    title='Algebra and Functions',
                    title_fr='Algebre et fonctions'),
    'diff': dict(order=3,
                 title='Differentiation',
                 title_fr='Derivation'),
    'integ': dict(order=4,
                  title='Integration',
                  title_fr='Integration'),
}

# chapter_key -> (order, title, title_fr, summary, summary_fr, objectives, objectives_fr)
LESSONS = [
    ('sequences', 2, 'Summation and Series', 'Sommation et series',
     'Use sigma notation and the standard sum formulas for arithmetic and '
     'geometric series.',
     'Utiliser la notation sigma et les formules classiques de somme des '
     'series arithmetiques et geometriques.',
     ['Interpret sigma notation',
      'Apply the sum formula for an arithmetic series',
      'Apply the sum formula for a geometric series'],
     ['Interpreter la notation sigma',
      'Appliquer la formule de somme d une serie arithmetique',
      'Appliquer la formule de somme d une serie geometrique']),
    ('algebra', 1, 'Quadratic Functions and the Discriminant',
     'Fonctions du second degre et discriminant',
     'Sketch a parabola and use the discriminant to count the real roots of a '
     'quadratic equation.',
     'Tracer une parabole et utiliser le discriminant pour compter les racines '
     'reelles d une equation du second degre.',
     ['Find the vertex and axis of symmetry of a parabola',
      'Compute the discriminant of a quadratic',
      'Use the discriminant to determine the number of real roots'],
     ['Trouver le sommet et l axe de symetrie d une parabole',
      'Calculer le discriminant d un trinome',
      'Utiliser le discriminant pour determiner le nombre de racines reelles']),
    ('algebra', 2, 'Solving Quadratic Inequalities',
     'Resoudre des inequations du second degre',
     'Solve inequalities by finding critical values and testing intervals on '
     'a sign diagram.',
     'Resoudre des inequations en trouvant les valeurs critiques et en testant '
     'les intervalles sur un tableau de signes.',
     ['Rearrange an inequality so one side is zero',
      'Find the critical values of a quadratic',
      'Write the solution set using interval notation'],
     ['Rearranger une inequation pour comparer a zero',
      'Trouver les valeurs critiques d un trinome',
      'Ecrire l ensemble solution en notation d intervalle']),
    ('diff', 1, 'Introduction to Differentiation',
     'Introduction a la derivation',
     'Find the gradient of a curve from first principles and use the power '
     'rule to differentiate polynomials.',
     'Trouver la pente d une courbe a partir des principes premiers et '
     'utiliser la regle de puissance pour deriver des polynomes.',
     ['Interpret the derivative as a gradient',
      'Differentiate a simple function from first principles',
      'Apply the power rule to polynomials'],
     ['Interpreter la derivee comme une pente',
      'Deriver une fonction simple a partir des principes premiers',
      'Appliquer la regle de puissance aux polynomes']),
    ('diff', 2, 'Stationary Points and Optimisation',
     'Points stationnaires et optimisation',
     'Locate stationary points, classify them with the second derivative, and '
     'solve optimisation problems.',
     'Localiser les points stationnaires, les classer avec la derivee seconde '
     'et resoudre des problemes d optimisation.',
     ['Find stationary points by solving f prime equals zero',
      'Classify points using the second derivative',
      'Solve simple optimisation problems'],
     ['Trouver les points stationnaires en resolvant f prime egal zero',
      'Classer les points avec la derivee seconde',
      'Resoudre des problemes d optimisation simples']),
    ('integ', 1, 'Integration as the Reverse of Differentiation',
     'L integration comme inverse de la derivation',
     'Reverse the power rule to find antiderivatives and evaluate indefinite '
     'integrals with the constant of integration.',
     'Inverser la regle de puissance pour trouver des primitives et calculer '
     'des integrales indefinies avec la constante d integration.',
     ['Recognise integration as antidifferentiation',
      'Integrate powers of x',
      'Remember the constant of integration'],
     ['Reconnaitre l integration comme antidifferentiation',
      'Integrer des puissances de x',
      'Ne pas oublier la constante d integration']),
    ('integ', 2, 'Definite Integrals and Area',
     'Integrales definies et aire',
     'Evaluate definite integrals and use them to find the area between a '
     'curve and the x axis.',
     'Calculer des integrales definies et les utiliser pour trouver l aire '
     'entre une courbe et l axe des abscisses.',
     ['Evaluate a definite integral using the limits',
      'Interpret a definite integral as an area',
      'Find the area between a curve and the x axis'],
     ['Calculer une integrale definie entre les bornes',
      'Interpreter une integrale definie comme une aire',
      'Trouver l aire entre une courbe et l axe des abscisses']),
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

# Sequences (13) reste la premiere lecon du chapitre des suites.
seq = Lesson.objects.filter(pk=13).first()
if seq:
    seq.chapter = chapters['sequences']
    seq.order = 1
    seq.estimated_minutes = max(seq.estimated_minutes, 30)
    seq.save(update_fields=['chapter', 'order', 'estimated_minutes'])

print('Chapitres :', {k: v.id for k, v in chapters.items()})
print('Nouvelles lecons creees :', created)
for key in ('sequences', 'algebra', 'diff', 'integ'):
    print(f'-- {chapters[key].title}')
    for l in chapters[key].lessons.order_by('order'):
        print(f'   id={l.id} order={l.order} {l.title!r} status={l.status}')
