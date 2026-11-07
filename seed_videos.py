"""Attache des videos YouTube verifiees aux lecons qui n'en avaient pas.

Chaque URL a ete validee via l'endpoint oEmbed de YouTube : la video existe et
son titre correspond bien au sujet de la lecon. Aucune URL n'est inventee.

La video est posee comme `lesson.video_url` (lecteur principal) ET comme
`Resource` de type video, afin d'apparaitre aussi dans le hub de la lecon
(le hub est le seul point d'acces pour les lecons a micro-etapes).

Lancer :
    venv\\Scripts\\python.exe manage.py shell -c "exec(open('seed_videos.py', encoding='utf-8').read())"
"""
from education.models import Lesson, Resource

# lesson_id -> (video_id, titre de la video, chaine)
VIDEOS = {
    1: ('2WS1sG9fhOk', 'Introduction to work and energy', 'Khan Academy'),
    3: ('kZzoVCmUyKg', 'Introduction to fractions', 'Khan Academy'),
    8: ('Ft2_QtXAnh8', 'Linear Equations - Algebra',
        'The Organic Chemistry Tutor'),
    13: ('bw9DICA8TDU',
         'Everything you need to know about IGCSE Sequences', 
         'Ginger Mathematician'),
    14: ('3f_eisNPpnc', 'Mendelian Genetics and Punnett Squares',
         'Professor Dave Explains'),
    18: ('LGRoPAPMZhA', 'Rounding Numbers and Rounding Decimals',
         'The Organic Chemistry Tutor'),
    19: ('BUJKEDqGp1U', 'Laws of Indices - Part 1', 'FuseSchool'),
    21: ('YgxUCo94-xk', 'Cube Numbers', 'corbettmaths'),
    22: ('o8mHyddtq3o', 'Collecting Like Terms and Simplifying Expressions',
         'Minity Maths'),
    24: ('dTwZ5N126gw',
         'Plotting a simple inequality on a number line', 'Khan Academy'),
    25: ('X-djBcWVizM', 'Factorising quadratics 1', 'corbettmaths'),
    26: ('IlNAJl36-10',
         'How To Solve Quadratic Equations Using The Quadratic Formula',
         'The Organic Chemistry Tutor'),
    27: ('phlus4x0UqM', 'Simultaneous Equations elimination', 'corbettmaths'),
    28: ('FD9DVFBpCMI', 'GCSE Maths - 5 Angle Rules to Know', 'Cognito'),
    29: ('10dTx1Zy_4w', 'Recognizing shapes', 'Khan Academy'),
    30: ('gVo8ZrtlSp0', 'Angles in Polygons', 'corbettmaths'),
    31: ('tN95TLKpmVQ',
         'Area of Rectangles, Parallelograms, Triangles and Trapeziums',
         'Cognito'),
    32: ('zuV1puxGMZQ', 'Circumference and Area of a Circle',
         'corbettmaths'),
    33: ('_QdIzOVcjNI', 'Volume of Cylinders & Prisms', 'Cognito'),
    34: ('AA6RfgP-AHU', 'The Pythagorean theorem intro', 'Khan Academy'),
    35: ('WFH_7n7hpHo', 'Trigonometry | SOH CAH TOA | Sin, Cos, Tan',
         'Cognito'),
    36: ('aoy7byO_nc0', 'Mean, Mode, Median and Range', 'MyGCSEMaths'),
    37: ('LEXbMW-Amao', 'Drawing Bar Charts', 'corbettmaths'),
    38: ('WqpwuIsBqWs', 'Probability', 'Maths Genie'),
    54: ('mfiYiJT3cqo', 'Solids, Liquids And Gases', 'Save My Exams'),
    56: ('kKKM8Y-u7ds', "Newton's Laws: Crash Course Physics #5",
         'CrashCourse'),
    57: ('mjeOuh0G-gw', 'Conservation of Momentum', 'Cognito'),
    58: ('m2P2DdfebiU', 'Density - Equation', 'Cognito'),
    59: ('ihNZlp7iUHE', 'Intro to vectors & scalars', 'Khan Academy'),
    60: ('RM02SnuJ0MY', 'Distance-Time Graphs', 'Cognito'),
    # AL Biologie
    66: ('qHkUOlC8Nbo', 'GCSE Biology - Cell Types and Cell Structure',
         'Cognito'),
    67: ('QN4hqLdC48g', 'A-Level Biology - Biological Molecules', 'Cognito'),
    68: ('lS3jX-yXXc4', 'A-Level Biology - Factors that Affect Enzyme Action',
         'Cognito'),
    69: ('vbdwTor6H14', 'Diffusion, Osmosis & Active Transport', 'Science Shorts'),
    70: ('vJjuJInJ6-Y',
         'A-Level Biology - Meiosis | Stages & Differences to Mitosis',
         'Cognito'),
    71: ('7ghUcw1c9ws',
         'Protein Synthesis: Transcription, translation and pre-mRNA',
         'Miss Estruch'),
    # Mathematiques al
    91: ('tiuLFj7dEq0', 'Sigma notation', 'Maths Genie'),
    92: ('6fU9ZgwbU74',
         'How To Determine The Discriminant of a Quadratic Equation',
         'The Organic Chemistry Tutor'),
    93: ('_gWjLKsFOPE', 'Quadratic Inequalities',
         'The Organic Chemistry Tutor'),
    94: ('9Yz-RCdS2Tg', 'The Power Rule For Derivatives',
         'The Organic Chemistry Tutor'),
    95: ('G8GAsYkZlpE', 'Second Derivative Test',
         'The Organic Chemistry Tutor'),
    96: ('WfTFcHIOurc', 'Integral Power Rule EXPLAINED with Examples',
         'Ace Tutors'),
    97: ('0dDIPzqKgYk', 'Definite integrals intro', 'Khan Academy'),
    # Chemistry ol
    107: ('ysqMGn4MNTU', 'GCSE Chemistry: Atoms', 'Cognito'),
    108: ('gTQspZGTEAc', 'Types of bonds: Ionic + Metallic + Covalent',
          'Cognito'),
    109: ('oQalH_mfOfg',
          'Balancing Equations - Writing Word & Symbol Equations', 'Cognito'),
    110: ('kBlmEfS_P00', "Moles & Mass - Avogadro's Constant", 'Cognito'),
    111: ('Yrf3Z_TQu_k',
          'Acids & Bases - pH | Features | Neutralisation Reactions', 'Cognito'),
    112: ('vcxlISVJ6Os', 'Neutralisation Reactions | Reactions of Acids',
          'Cognito'),
    113: ('29Rd-Lly-fw',
          'Separation Techniques - Filtration | Evaporation | Crystallisation',
          'Cognito'),
    114: ('NBw5s7cuwMc',
          'The Reactivity Series - Metal Reactions | Displacement Reactions',
          'Cognito'),
    115: ('H0Z_R6GLo9A',
          "Air Pollution - How Pollutants are Made | Why They're Harmful",
          'Cognito'),
    123: ('JK7yPzO9POU',
          'Factors Affecting Rate of Reaction & Collision Theory', 'Cognito'),
    124: ('hNNvIsQLSV8',
          'Exothermic & Endothermic Reactions - Reaction Profiles | Activation '
          'Energy', 'Cognito'),
    125: ('-qxeVFJh4e4',
          'Fractional Distillation - Crude Oil | Hydrocarbons', 'Cognito'),
    126: ('LfweGr7Y8L4',
          'Cracking & Alkenes - Catalytic & Steam Cracking | Equations',
          'Cognito'),
    140: ('RAEm-kJ_QkU',
          'Electrolysis Part 1/3 - Basics and Molten Compounds', 'Cognito'),
    141: ('me19WmGg8Dw', 'Electrolysis Part 3/3 - Aqueous Solutions',
          'Cognito'),
    142: ('bcRGfSlMIMw',
          'How to Test for Gases - Chlorine / Oxygen / Hydrogen / CO2',
          'Cognito'),
    143: ('mWTgHjdea4Y',
          'Tests for Anions - Carbonate, Sulfate and Halide Ions', 'Cognito'),
}

count = 0
for lesson_id, (video_id, title, channel) in VIDEOS.items():
    lesson = Lesson.objects.filter(pk=lesson_id).first()
    if lesson is None:
        print(f'[skip] lecon {lesson_id} introuvable')
        continue
    url = f'https://www.youtube.com/watch?v={video_id}'

    if lesson.video_url != url:
        lesson.video_url = url
        lesson.save(update_fields=['video_url'])

    resource, created = Resource.objects.get_or_create(
        lesson=lesson, kind=Resource.Kind.VIDEO, url=url,
        defaults={'order': 1, 'title': f'{title} ({channel})',
                  'source_name': channel,
                  'license_note': f'Video educative - {channel} '
                                  f'(partage YouTube)'})
    if not created:
        resource.order = 1
        resource.title = f'{title} ({channel})'
        resource.source_name = channel
        resource.license_note = f'Video educative - {channel} (partage YouTube)'
        resource.save()

    # Les fiches PDF passent en ordre 2 et 3, apres la video.
    for res in lesson.resources.filter(kind=Resource.Kind.PDF):
        if res.title.startswith('Practice worksheet'):
            res.order = 2
        elif res.title.startswith('Answer key'):
            res.order = 3
        res.save(update_fields=['order'])

    count += 1
    print(f'[OK] {lesson_id} {lesson.title} -> {title} ({channel})')

print(f'[TERMINE] {count} video(s) attachee(s).')
