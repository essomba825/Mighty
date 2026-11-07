# Cree la structure du module GCE Ordinary Level Chemistry (idempotent).
# Usage : ..\venv\Scripts\python.exe manage.py shell -c "exec(open('seed_chemistry_ol.py',encoding='utf-8').read())"
from education.models import Subject, Chapter, Lesson

SUBJECT_ID = 8

CHAPTERS = {
    'structure': dict(order=3,
                      title='Atomic Structure, Bonding and the Periodic Table',
                      title_fr='Structure atomique, liaison et tableau périodique'),
    'equations': dict(order=4,
                      title='Chemical Equations and the Mole',
                      title_fr='Équations chimiques et la mole'),
    'acids': dict(order=5,
                  title='Acids, Bases and Salts',
                  title_fr='Acides, bases et sels'),
    'separation': dict(order=6,
                       title='Separation Techniques',
                       title_fr='Techniques de séparation'),
    'metals': dict(order=7,
                   title='Metals and the Reactivity Series',
                   title_fr='Métaux et série de réactivité'),
    'air': dict(order=8,
                title='Air, Water and Combustion',
                title_fr='Air, eau et combustion'),
    'rates': dict(order=9,
                  title='Rates of Reaction and Energy Changes',
                  title_fr="Vitesse de réaction et changements d'énergie"),
    'organic': dict(order=10,
                    title='Organic Chemistry and Fuels',
                    title_fr='Chimie organique et carburants'),
    'electrolysis': dict(order=11,
                         title='Electrolysis',
                         title_fr='Électrolyse'),
    'tests': dict(order=12,
                  title='Chemical Tests and Analysis',
                  title_fr='Tests chimiques et analyse'),
}

# chapter_key -> (order, title, title_fr, summary, summary_fr, objectives, objectives_fr)
LESSONS = [
    ('structure', 1, 'Atomic Structure and the Periodic Table',
     'Structure atomique et tableau périodique',
     'Describe the structure of the atom and use proton and electron numbers '
     'to place elements in the periodic table.',
     "Décrire la structure de l'atome et utiliser le nombre de protons et "
     "d'électrons pour placer les éléments dans le tableau périodique.",
     ['Describe protons, neutrons and electrons in an atom',
      'Work out proton, neutron and electron numbers',
      'Relate group and period to electron arrangement'],
     ["Décrire les protons, neutrons et électrons d'un atome",
      'Calculer les nombres de protons, neutrons et électrons',
      'Relier groupe et période à la structure électronique']),
    ('structure', 2, 'Chemical Bonding: Ionic and Covalent',
     'Liaison chimique : ionique et covalente',
     'Explain how atoms join by transferring or sharing electrons to form '
     'ionic and covalent compounds.',
     "Expliquer comment les atomes s'unissent en transférant ou partageant "
     'des électrons pour former des composés ioniques et covalents.',
     ['Explain ionic bonding as electron transfer',
      'Explain covalent bonding as electron sharing',
      'Relate bonding to properties such as melting point'],
     ["Expliquer la liaison ionique comme un transfert d'électrons",
      "Expliquer la liaison covalente comme un partage d'électrons",
      'Relier la liaison aux propriétés comme la température de fusion']),
    ('equations', 1, 'Word and Symbol Equations',
     'Équations en mots et en symboles',
     'Turn word equations into balanced symbol equations using state symbols '
     'and correct formulas.',
     'Transformer des équations en mots en équations symboliques équilibrées '
     "avec les formules et les états physiques.",
     ['Turn a word equation into a symbol equation',
      'Balance a simple chemical equation',
      'Use state symbols (s), (l), (g), (aq)'],
     ['Transformer une équation en mots en équation symbolique',
      'Équilibrer une équation chimique simple',
      "Utiliser les symboles d'état (s), (l), (g), (aq)"]),
    ('equations', 2, 'The Mole Concept and Calculations',
     'La mole et les calculs',
     'Use the mole, molar mass and Avogadro constant to calculate masses and '
     'amounts in simple reactions.',
     "Utiliser la mole, la masse molaire et le nombre d'Avogadro pour calculer "
     'des masses et des quantités dans des réactions simples.',
     ['Define the mole and Avogadro constant',
      'Calculate moles from mass and molar mass',
      'Use a balanced equation to compare reacting amounts'],
     ["Définir la mole et le nombre d'Avogadro",
      'Calculer les moles à partir de la masse et de la masse molaire',
      'Utiliser une équation équilibrée pour comparer les quantités']),
    ('acids', 1, 'Acids and Bases',
     'Acides et bases',
     'Recognise acids and bases and use indicators and pH to describe their '
     'strength.',
     'Reconnaître les acides et les bases et utiliser les indicateurs et le pH '
     'pour décrire leur force.',
     ['Describe the properties of acids and bases',
      'Use litmus, phenolphthalein and pH values',
      'Explain acids in terms of hydrogen ions'],
     ['Décrire les propriétés des acides et des bases',
      'Utiliser le tournesol, la phénolphtaléine et les valeurs de pH',
      'Expliquer les acides en termes d\'ions hydrogène']),
    ('acids', 2, 'Salts and Neutralisation',
     'Sels et neutralisation',
     'Write neutralisation reactions and prepare common salts by choosing the '
     'right acid and base.',
     'Écrire les réactions de neutralisation et préparer des sels courants en '
     'choisissant le bon acide et la bonne base.',
     ['Explain neutralisation producing a salt and water',
      'Predict the salt formed by an acid and a base',
      'Describe preparing a soluble salt'],
     ['Expliquer la neutralisation qui donne un sel et de l\'eau',
      'Prévoir le sel formé par un acide et une base',
      'Décrire la préparation d\'un sel soluble']),
    ('separation', 1, 'Separating Mixtures',
     'Séparer les mélanges',
     'Choose and carry out the right technique to separate the parts of a '
     'mixture, such as filtration, evaporation or distillation.',
     'Choisir et appliquer la bonne technique pour séparer les constituants '
     "d'un mélange : filtration, évaporation ou distillation.",
     ['Separate an insoluble solid by filtration',
      'Recover a dissolved solid by evaporation',
      'Separate a solvent and solute by distillation'],
     ['Séparer un solide insoluble par filtration',
      'Récupérer un solide dissous par évaporation',
      'Séparer un solvant et un soluté par distillation']),
    ('metals', 1, 'The Reactivity Series of Metals',
     'La série de réactivité des métaux',
     'Order metals by reactivity and use the series to predict reactions and '
     'methods of extraction.',
     'Classer les métaux par réactivité et utiliser la série pour prévoir les '
     "réactions et les méthodes d'extraction.",
     ['Place common metals in order of reactivity',
      'Predict displacement reactions using the series',
      'Relate reactivity to the method of extraction'],
     ['Classer des métaux courants par ordre de réactivité',
      'Prévoir les réactions de déplacement grâce à la série',
      "Relier la réactivité à la méthode d'extraction"]),
    ('air', 1, 'Air, Water and Combustion',
     'Air, eau et combustion',
     'Describe the composition of clean air and water and explain what happens '
     'during combustion.',
     "Décrire la composition de l'air propre et de l'eau et expliquer ce qui se "
     'passe lors de la combustion.',
     ['State the composition of clean air',
      'Explain combustion and the tests for its products',
      'Describe the composition and purification of water'],
     ["Donner la composition de l'air propre",
      'Expliquer la combustion et les tests de ses produits',
      "Décrire la composition et la purification de l'eau"]),
    ('rates', 1, 'Rates of Reaction',
     'Vitesse de réaction',
     'Explain how concentration, temperature, surface area and catalysts '
     'change how fast a chemical reaction happens.',
     "Expliquer comment la concentration, la température, la surface de "
     "contact et les catalyseurs modifient la vitesse d'une réaction.",
     ['Describe how the speed of a reaction can be measured',
      'Explain collision theory and the effect of concentration, temperature '
      'and surface area',
      'Explain how a catalyst speeds up a reaction'],
     ["Décrire comment mesurer la vitesse d'une réaction",
      "Expliquer la théorie des collisions et l'effet de la concentration, de "
      "la température et de la surface de contact",
      "Expliquer comment un catalyseur accélère une réaction"]),
    ('rates', 2, 'Energy Changes in Reactions',
     "Changements d'énergie dans les réactions",
     'Tell apart exothermic and endothermic reactions and use energy level '
     'diagrams to show the energy change.',
     "Distinguer les réactions exothermiques et endothermiques et utiliser les "
     "diagrammes d'énergie pour montrer le changement d'énergie.",
     ['Define exothermic and endothermic reactions',
      'Interpret energy level diagrams',
      'Explain energy changes in terms of bonds broken and bonds made'],
     ['Définir les réactions exothermiques et endothermiques',
      "Interpréter les diagrammes d'énergie",
      "Expliquer les changements d'énergie par les liaisons rompues et formées"]),
    ('organic', 1, 'Crude Oil and Hydrocarbons',
     'Pétrole brut et hydrocarbures',
     'Describe how crude oil is separated into useful fractions and what a '
     'hydrocarbon is.',
     "Décrire comment le pétrole brut est séparé en fractions utiles et ce "
     "qu'est un hydrocarbure.",
     ['Describe crude oil as a mixture of hydrocarbons',
      'Explain fractional distillation of crude oil',
      'Relate the fractions to their everyday uses'],
     ['Décrire le pétrole brut comme un mélange d\'hydrocarbures',
      'Expliquer la distillation fractionnée du pétrole brut',
      'Relier les fractions à leurs usages courants']),
    ('organic', 2, 'Alkanes, Alkenes and Polymers',
     'Alcanes, alcènes et polymères',
     'Recognise alkanes and alkenes and explain cracking, addition and the '
     'formation of polymers.',
     "Reconnaître les alcanes et les alcènes et expliquer le craquage, "
     "l'addition et la formation des polymères.",
     ['Write the formulas of simple alkanes and alkenes',
      'Explain cracking and the test for alkenes',
      'Describe how alkenes join to make polymers'],
     ['Écrire les formules d\'alcanes et d\'alcènes simples',
      'Expliquer le craquage et le test des alcènes',
      'Décrire comment les alcènes s\'unissent pour former des polymères']),
    ('electrolysis', 1, 'Electrolysis and Electrodes',
     'Électrolyse et électrodes',
     'Explain how electrolysis uses electricity to break down ionic compounds '
     'and describe the role of the electrodes.',
     "Expliquer comment l'électrolyse utilise l'électricité pour décomposer "
     'des composés ioniques et décrire le rôle des électrodes.',
     ['Describe electrolysis as the movement of ions to the electrodes',
      'Identify the cathode and the anode and their charges',
      'Write the reactions at each electrode for a molten compound'],
     ["Décrire l'électrolyse par le déplacement des ions vers les électrodes",
      'Identifier la cathode et l\'anode ainsi que leurs charges',
      'Écrire les réactions aux électrodes pour un composé fondu']),
    ('electrolysis', 2, 'Electrolysis of Aqueous Solutions',
     'Électrolyse des solutions aqueuses',
     'Use the products of electrolysis to explain electroplating and the '
     'extraction of reactive metals.',
     "Utiliser les produits de l'électrolyse pour expliquer la galvanoplastie "
     'et l\'extraction des métaux réactifs.',
     ['Predict the products at each electrode for a salt solution',
      'Describe how copper is purified by electrolysis',
      'Explain electroplating of a metal object'],
     ['Prévoir les produits à chaque électrode pour une solution de sel',
      'Décrire la purification du cuivre par électrolyse',
      'Expliquer la galvanoplastie d\'un objet métallique']),
    ('tests', 1, 'Tests for Gases',
     'Tests des gaz',
     'Identify common gases using simple tests such as the glowing splint and '
     'limewater.',
     "Identifier des gaz courants grâce à des tests simples comme la bûchette "
     'incandescente et l\'eau de chaux.',
     ['Describe the test for oxygen, hydrogen and carbon dioxide',
      'Describe the test for chlorine and for ammonia',
      'Choose a suitable test to identify an unknown gas'],
     ['Décrire le test du dioxygène, du dihydrogène et du dioxyde de carbone',
      'Décrire le test du chlore et celui de l\'ammoniac',
      'Choisir le bon test pour identifier un gaz inconnu']),
    ('tests', 2, 'Tests for Ions and Flame Tests',
     'Tests des ions et tests de flamme',
     'Identify common metal ions by flame tests and use simple solutions to '
     'test for anions.',
     'Identifier des ions métalliques courants par des tests de flamme et '
     'détecter les anions avec des solutions simples.',
     ['Use flame colours to identify common metal ions',
      'Describe a test for chloride, sulfate and carbonate ions',
      'Choose a suitable test to identify an unknown salt'],
     ['Identifier des métaux courants grâce à la couleur de leur flamme',
      'Décrire les tests des ions chlorure, sulfate et carbonate',
      'Choisir le bon test pour identifier un sel inconnu']),
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

print('Chapitres :', {k: v.id for k, v in chapters.items()})
print('Nouvelles lecons creees :', created)
for key in CHAPTERS:
    print(f'-- {chapters[key].title}')
    for l in chapters[key].lessons.order_by('order'):
        print(f'   id={l.id} order={l.order} {l.title!r} status={l.status}')
