# Genere les fiches d'exercices + corriges PDF pour les lecons.
# Usage : ..\venv\Scripts\python.exe education/content/gen_lesson_pdfs.py
# Les fichiers tombent dans media/resources/ (servis par nginx en production).
# Pour une nouvelle lecon : ajouter un bloc de donnees + deux appels build().
import os

from fpdf import FPDF

OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'media', 'resources')
os.makedirs(OUT, exist_ok=True)

PRIMARY = (16, 30, 60)      # navy
ACCENT = (201, 162, 39)     # gold

class Doc(FPDF):
    """Portrait A4 : bandeau navy en haut, ligne d'or sous chaque exercice."""

    def __init__(self, title, subtitle):
        super().__init__(unit='mm', format='A4')
        self.title_txt = title
        self.subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=18)
        self.set_font('helvetica', '', 11)

    def header(self):
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 22, style='F')
        self.set_text_color(255, 215, 120)
        self.set_font('helvetica', 'B', 14)
        self.set_xy(10, 5)
        self.cell(0, 7, self.title_txt, new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(220, 226, 236)
        self.set_font('helvetica', '', 9)
        self.cell(0, 5, self.subtitle, new_x='LMARGIN', new_y='NEXT')
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_text_color(120, 128, 140)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 6, 'Mega Mighty Sixers - contenu original, diffusion libre aux membres de l association',
                  align='C')

    def titre_exo(self, n, txt):
        self.ln(1)
        self.set_text_color(*PRIMARY)
        self.set_font('helvetica', 'B', 11)
        self.multi_cell(0, 6, f'{n}. {txt}', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(2)

    def body(self, txt, italic=False):
        self.set_text_color(30, 34, 42)
        self.set_font('helvetica', 'I' if italic else '', 10.5)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5.4, txt, new_x='LMARGIN', new_y='NEXT')


def build(path, title, subtitle, exos, with_solutions):
    """exos : liste de dicts {en, fr, sol}."""
    pdf = Doc(title, subtitle)
    pdf.add_page()
    if with_solutions:
        pdf.body("Detailed method for every exercise. Follow the substitutions line by line.", italic=True)
        pdf.body("Corrige detaille de chaque exercice. Suis les substitutions ligne par ligne.", italic=True)
    else:
        pdf.body("Complete each exercise on paper, writing every step of your reasoning, "
                 "then compare with the separate answer key.", italic=True)
        pdf.body("Fais chaque exercice sur une feuille en detaillant ton raisonnement, "
                 "puis compare avec le corrige separe.", italic=True)
    pdf.ln(4)
    for i, ex in enumerate(exos, start=1):
        pdf.titre_exo(i, ex['en'])
        pdf.body(ex['en_txt'])
        pdf.body(ex['fr_txt'])
        if with_solutions:
            pdf.ln(1)
            pdf.titre_exo(i, 'Corrige / Answer')
            pdf.body(ex['sol'])
        pdf.ln(3)
    pdf.output(os.path.join(OUT, path))
    print('ecrit:', os.path.join(OUT, path))


# ---------------------------------------------------------------- Motion : speed
SPEED = dict(
    fr_slug='vitesse et mouvement',
    exos=[
        dict(en="Exercise 1 - Average speed",
             en_txt="A van covers 150 km in 2 h 30 min on the Yaounde-Bafoussam road. "
                    "Compute its average speed in km/h, then in m/s.",
             fr_txt="Un bus parcourt 150 km en 2 h 30 sur la route Yaounde-Bafoussam. "
                    "Calcule sa vitesse moyenne en km/h, puis en m/s.",
             sol="Ex. 1 - 2 h 30 = 2,5 h. v = 150 / 2,5 = 60 km/h. En m/s : 60 x 1000 / 3600 = 16,7 m/s environ."),
        dict(en="Exercise 2 - Unit conversion",
             en_txt="Convert 25 m/s into km/h.",
             fr_txt="Convertis 25 m/s en km/h.",
             sol="Ex. 2 - 1 m/s = 3,6 km/h, donc 25 x 3,6 = 90 km/h."),
        dict(en="Exercise 3 - Unit conversion, the other way",
             en_txt="Convert 108 km/h into m/s.",
             fr_txt="Convertis 108 km/h en m/s.",
             sol="Ex. 3 - On divise par 3,6 : 108 / 3,6 = 30 m/s."),
        dict(en="Exercise 4 - From the graph",
             en_txt="A cyclist moves with a constant speed of 8 m/s during 50 s. "
                    "What distance does he cover?",
             fr_txt="Un cycliste roule a vitesse constante de 8 m/s pendant 50 s. "
                    "Quelle distance parcourt-il ?",
             sol="Ex. 4 - Mouvement uniforme : d = v x t = 8 x 50 = 400 m."),
        dict(en="Exercise 5 - Uniform or not?",
             en_txt="A runner's speed stays at 5 m/s for 200 m, then drops to 3 m/s "
                    "for the last 100 m. Is the whole motion uniform? Justify.",
             fr_txt="La vitesse d'un coureur vaut 5 m/s sur 200 m, puis tombe a 3 m/s "
                    "sur les derniers 100 m. Le mouvement complet est-il uniforme ? Justifie.",
             sol="Ex. 5 - Non : la vitesse change (5 m/s puis 3 m/s). Le mouvement n'est uniforme que si la vitesse reste constante."),
        dict(en="Exercise 6 - Average over a journey",
             en_txt="A car drives 60 km in 1 h, then 120 km in 1 h. "
                    "Compute the average speed over the whole journey. "
                    "Is it the mean of the two speeds?",
             fr_txt="Une voiture parcourt 60 km en 1 h, puis 120 km en 1 h. "
                    "Calcule la vitesse moyenne sur tout le trajet. "
                    "Est-ce la moyenne des deux vitesses ?",
             sol="Ex. 6 - v_moyenne = distance totale / temps total = (60 + 120) / (1 + 1) = 90 km/h. "
                 "La moyenne des vitesses donne aussi 90 km/h, mais seulement parce que les durees sont egales ; "
                 "en general il faut toujours diviser la distance totale par le temps total."),
    ],
)

# ------------------------------------------------------- Motion : acceleration
ACCEL = [
    dict(en="Exercise 1 - A first acceleration",
         en_txt="A taxi leaves the taxi rank at 3 m/s and reaches 13 m/s in 10 s on the avenue. "
                "Compute its acceleration in m/s^2.",
         fr_txt="Un taxi quitte la station a 3 m/s et atteint 13 m/s en 10 s sur l'avenue. "
                "Calcule son acceleration en m/s^2.",
         sol="Ex. 1 - a = delta_v / delta_t = (13 - 3) / 10 = 10 / 10 = 1 m/s^2. "
             "Le taxi gagne 1 m/s chaque seconde."),
    dict(en="Exercise 2 - Convert first, then compute",
         en_txt="A car goes from rest to 90 km/h in 6 s. "
                "Convert 90 km/h into m/s first, then find the acceleration.",
         fr_txt="Une voiture passe de l'arret a 90 km/h en 6 s. "
                "Convertis d'abord 90 km/h en m/s, puis calcule l'acceleration.",
         sol="Ex. 2 - 90 km/h = 90 / 3,6 = 25 m/s. a = delta_v / delta_t = (25 - 0) / 6 = 4,2 m/s^2 environ."),
    dict(en="Exercise 3 - Braking, the negative case",
         en_txt="A moto brakes from 15 m/s to a standstill in 3 s. "
                "Compute the acceleration and explain the minus sign.",
         fr_txt="Une moto freine de 15 m/s jusqu'a l'arret en 3 s. "
                "Calcule l'acceleration et explique le signe moins.",
         sol="Ex. 3 - a = (0 - 15) / 3 = -5 m/s^2. "
             "Le signe moins indique une vitesse qui diminue : c'est un freinage (deceleration)."),
    dict(en="Exercise 4 - From a speed-time graph",
         en_txt="On a speed-time graph the line climbs from 2 m/s at t = 1 s to 10 m/s at t = 9 s. "
                "What is the acceleration?",
         fr_txt="Sur un graphe vitesse-temps, la ligne monte de 2 m/s a t = 1 s jusqu'a 10 m/s a t = 9 s. "
                "Quelle est l'acceleration ?",
         sol="Ex. 4 - Pente = (10 - 2) / (9 - 1) = 8 / 8 = 1 m/s^2."),
    dict(en="Exercise 5 - Which one accelerates more?",
         en_txt="Runner A goes from 2 m/s to 14 m/s in 6 s; runner B goes from rest "
                "to 15 m/s in 5 s. Which runner has the greater acceleration?",
         fr_txt="Le coureur A passe de 2 m/s a 14 m/s en 6 s ; le coureur B passe de l'arret "
                "a 15 m/s en 5 s. Quel est le plus fort en acceleration ?",
         sol="Ex. 5 - A : (14 - 2) / 6 = 2 m/s^2. B : (15 - 0) / 5 = 3 m/s^2. "
             "B accelere le plus vite, meme si B part de zero."),
    dict(en="Exercise 6 - Braking distance in time",
         en_txt="A truck loses speed at a steady -4 m/s^2 starting from 20 m/s. "
                "How many seconds does it take to stop completely?",
         fr_txt="Un camion perd sa vitesse a -4 m/s^2 constants depuis 20 m/s. "
                "Combien de secondes faut-il pour s'arreter completement ?",
         sol="Ex. 6 - a = delta_v / delta_t donc delta_t = delta_v / a = (0 - 20) / (-4) = (-20) / (-4) = 5 s."),
]


# -------------------------------------------------------------- Forces / poids
FORCES = [
    dict(en="Exercise 1 - Everyday weights",
         en_txt="A school bag has a mass of 3 kg. Using g = 10 N/kg, compute its weight in newtons.",
         fr_txt="Un sac d'ecole a une masse de 3 kg. Avec g = 10 N/kg, calcule son poids en newtons.",
         sol="Ex. 1 - W = m g = 3 x 10 = 30 N."),
    dict(en="Exercise 2 - From weight back to mass",
         en_txt="A crate on a stall is pulled down by a weight of 120 N (g = 10 N/kg). "
                "What is its mass in kilograms?",
         fr_txt="Une caisse sur un etal est attiree vers le bas par un poids de 120 N (g = 10 N/kg). "
                "Quelle est sa masse en kilogrammes ?",
         sol="Ex. 2 - m = W / g = 120 / 10 = 12 kg."),
    dict(en="Exercise 3 - Trip to the Moon",
         en_txt="The same 3 kg bag is carried to the Moon, where g = 1.6 N/kg. "
                "What is its weight there? What is its mass there?",
         fr_txt="Le meme sac de 3 kg est emporte sur la Lune, ou g = 1,6 N/kg. "
                "Quel est son poids la-bas ? Et sa masse ?",
         sol="Ex. 3 - Poids = 3 x 1,6 = 4,8 N. La masse reste inchangee : 3 kg."),
    dict(en="Exercise 4 - Reading a spring balance",
         en_txt="A dynamometer reads 4 N when a bag of fruit is hung on it (g = 10 N/kg). "
                "What is the mass of the fruit, in kilograms and then in grams?",
         fr_txt="Un dynamometre indique 4 N quand on y accroche un sachet de fruits (g = 10 N/kg). "
                "Quelle est la masse des fruits, en kilogrammes puis en grammes ?",
         sol="Ex. 4 - m = W / g = 4 / 10 = 0,4 kg = 400 g."),
    dict(en="Exercise 5 - From grams to newtons",
         en_txt="A textbook has a mass of 500 g. What force does the Earth apply to it "
                "(g = 10 N/kg)? Watch the units first.",
         fr_txt="Un manuel a une masse de 500 g. Quelle force la Terre exerce-t-elle sur lui "
                "(g = 10 N/kg) ? Attention aux unites d'abord.",
         sol="Ex. 5 - 500 g = 0,5 kg. W = 0,5 x 10 = 5 N."),
    dict(en="Exercise 6 - Mission to Mars",
         en_txt="A 70 kg astronaut lands on Mars, where g = 3.7 N/kg. "
                "Compute his weight on Mars and compare with his weight on Earth (g = 10 N/kg).",
         fr_txt="Un astronaute de 70 kg atterrit sur Mars, ou g = 3,7 N/kg. "
                "Calcule son poids sur Mars et compare avec son poids sur Terre (g = 10 N/kg).",
         sol="Ex. 6 - Mars : 70 x 3,7 = 259 N. Terre : 70 x 10 = 700 N. "
             "Le poids martien vaut environ 37% du poids terrestre, la masse reste 70 kg."),
]


# ------------------------------------------------- Frottements et resultantes
FRICTION = [
    dict(en="Exercise 1 - Useful or harmful",
         en_txt="For each of these, say if friction is useful or harmful: "
                "a) the sole of a shoe on a wet floor, b) the axle of a bike wheel, "
                "c) the brake pads of a car.",
         fr_txt="Pour chacun, dis si le frottement est utile ou genant : "
                "a) la semelle d'une chaussure sur sol mouille, b) l'axe d'une roue de velo, "
                "c) les plaquettes de frein d'une voiture.",
         sol="Ex. 1 - a) utile : sans grip on glisse. b) genant : il use et freine l'axe, on le graisse. "
             "c) utile : il permet de freiner."),
    dict(en="Exercise 2 - One direction only",
         en_txt="Two porters push a sofa with 300 N and 400 N in the same direction. "
                "What is the size of the resultant force?",
         fr_txt="Deux porteurs poussent un canape avec 300 N et 400 N dans le meme sens. "
                "Quelle est la valeure de la force resultante ?",
         sol="Ex. 2 - Meme sens, on additionne : 300 + 400 = 700 N."),
    dict(en="Exercise 3 - Tug of war",
         en_txt="A rope game pulls 450 N to the right and 250 N to the left. "
                "Compute the resultant force, with its direction.",
         fr_txt="Un jeu de corde tire 450 N vers la droite et 250 N vers la gauche. "
                "Calcule la resultante, avec son sens.",
         sol="Ex. 3 - Sens opposes, on soustrait : 450 - 250 = 200 N vers la droite."),
    dict(en="Exercise 4 - Fighting friction",
         en_txt="A crate is driven by a resultant of 0 N over the ground while someone pushes "
                "with 180 N. What is the friction force from the ground?",
         fr_txt="Une caisse avance sous une resultante de 0 N pendant qu'on la pousse "
                "avec 180 N. Quelle est la force de frottement du sol ?",
         sol="Ex. 4 - Resultante nulle : les forces s'equilibrent ; le frottement vaut 180 N en sens contraire."),
    dict(en="Exercise 5 - Unbalanced",
         en_txt="Weight of a crate : 500 N downward. Normal force from a table : 500 N upward. "
                "What is the resultant in the vertical direction?",
         fr_txt="Poids d'une caisse : 500 N vers le bas. Force normale de la table : 500 N vers le haut. "
                "Quelle est la resultante verticale ?",
         sol="Ex. 5 - 500 - 500 = 0 N : les forces verticales sont equilibrees."),
    dict(en="Exercise 6 - Balance or change",
         en_txt="States if the motion changes or stays identical : "
                "a) a car at rest with resultant 0 N, b) a sprinter accelerating, resultant 120 N, "
                "c) a pontoon boat at constant velocity on a lake.",
         fr_txt="Dis si le mouvement change ou reste identique : "
                "a) une voiture a l'arret, resultante 0 N, b) un sprinter qui accelere, resultante 120 N, "
                "c) un bateau a vitesse constante sur un lac.",
         sol="Ex. 6 - a) inchangé. b) change (acceleration). c) inchangé : resultante nulle malgré le mouvement."),
]


# --------------------------------------------- Chimie : atomes, elements, composes
ATOMS = [
    dict(en="Exercise 1 - Sort the three families",
         en_txt="Classify each item as element, compound or mixture: "
                "a) iron nails, b) carbon dioxide, c) sea water, d) oxygen gas.",
         fr_txt="Classe chaque item comme element, compose ou melange : "
                "a) les clous en fer, b) le dioxyde de carbone, c) l'eau de mer, d) le gaz oxygene.",
         sol="Ex. 1 - a) element (une seule sorte d'atomes). b) compose. c) melange. d) element."),
    dict(en="Exercise 2 - Read the formula",
         en_txt="State how many atoms of each element are inside one molecule of: "
                "a) H2 (hydrogen gas), b) H2O (water), c) CO2 (carbon dioxide).",
         fr_txt="Dis combien d'atomes de chaque element contient une molecule de : "
                "a) H2 (gaz hydrogene), b) H2O (eau), c) CO2 (dioxyde de carbone).",
         sol="Ex. 2 - a) 2 H. b) 2 H et 1 O. c) 1 C et 2 O. Les indices suivent leur lettre de gauche."),
    dict(en="Exercise 3 - The kitchen test",
         en_txt="Sugar cube, air, tap water, pure copper wire: which is a compound? Justify.",
         fr_txt="Cube de sucre, air, eau du robinet, fil de cuivre pur : "
                "lequel est un compose ? Justifie.",
         sol="Ex. 3 - Le sucre est un compose (C, H, O unis chimiquement) ; l'air et l'eau du robinet "
             "sont des melanges ; le cuivre est un element."),
    dict(en="Exercise 4 - Separation as a clue",
         en_txt="Salt water loses its water on gentle boiling and leaves salt behind. "
                "What does this prove about salt water?",
         fr_txt="L'eau salee perd son eau par legere ebullition et laisse le sel. "
                "Qu'est-ce que cela prouve sur l'eau salee ?",
         sol="Ex. 4 - C'est un melange, car ses constituants se separent sans changement chimique."),
    dict(en="Exercise 5 - Count the atoms",
         en_txt="Count the total number of atoms in one molecule of glucose: C6H12O6.",
         fr_txt="Compte le nombre total d'atomes dans une molecule de glucose : C6H12O6.",
         sol="Ex. 5 - 6 + 12 + 6 = 24 atomes au total."),
    dict(en="Exercise 6 - Harder: mixtures versus compounds",
         en_txt="Explain in one or two sentences why rust (iron oxide) is a compound "
                "while the mixture of iron filings and sulfur is only a mixture.",
         fr_txt="Explique en une ou deux phrases pourquoi la rouille (oxyde de fer) est un compose "
                "alors qu'un melange de limaille de fer et de soufre n'est qu'un melange.",
         sol="Ex. 6 - Dans la rouille, Fe et O se sont unis chimiquement et ne se separent plus par "
             "des gestes simples ; dans la limaille + soufre, un aimant ou un tamis separe encore les deux."),
]


# ------------------------------------------------------------- Chimie : diffusion
DIFFUSION = [
    dict(en="Exercise 1 - Spot the definition",
         en_txt="Finish the sentence: diffusion is the spreading of particles "
                "from a region where they are ... to a region where they are ... .",
         fr_txt="Complete : la diffusion est l'etalement des particules "
                "d'une region ou elles sont ... vers une region ou elles sont ... .",
         sol="Ex. 1 - ... nombreuses ... vers ... rares (jusqu'a l'equilibre)."),
    dict(en="Exercise 2 - Fast or slow",
         en_txt="Rank from fastest to slowest diffusion: color in still water, perfume in air, salt inside a solid block.",
         fr_txt="Classe de la plus rapide a la plus lente : couleur dans de l'eau immobile, parfum dans l'air, sel dans un bloc solide.",
         sol="Ex. 2 - Parfum dans l'air (gaz) > couleur dans l'eau (liquide) > sel dans le bloc (solide, quasi nul)."),
    dict(en="Exercise 3 - Turn the heat up",
         en_txt="The same dye spreads in a glass of cold water and in a glass of warm water. "
                "Where does it spread faster, and why (one sentence)?",
         fr_txt="Le meme colorant s'etale dans un verre d'eau froide et dans un verre d'eau chaude. "
                "Dans lequel va-t-il plus vite, et pourquoi (une phrase) ?",
         sol="Ex. 3 - Dans l'eau chaude : les particules plus chaudes se bousculent plus fort."),
    dict(en="Exercise 4 - The sealed cupboard",
         en_txt="A sealed tin keeps dry biscuits in a cupboard. After one year, the cupboard air still has no biscuit smell. "
                "Use particle ideas to explain why.",
         fr_txt="Une boite fermee garde des biscuits au sec dans un placard. Apres un an, l'air du placard ne sent toujours rien. "
                "Explique pourquoi avec l'idee des particules.",
         sol="Ex. 4 - Les biscuits sont des solides : leurs particules sont bloquees en reseau, la diffusion vers l'air est quasi impossible."),
    dict(en="Exercise 5 - Perfume at home",
         en_txt="A perfume sprayed on the balcony reaches the stairs within a minute. "
                "Which state of matter helps it so much, and how?",
         fr_txt="Un parfum pulverise sur le balcon atteint l'escalier en une minute. "
                "Quel etat de la matiere l'aide autant, et comment ?",
         sol="Ex. 5 - Le gaz : les particules y sont libres et parcourent de grandes distances entre collisions."),
    dict(en="Exercise 6 - Unfold the purple crystal",
         en_txt="Describe what happens when a crystal of potassium permanganate is dropped into still water. "
                "Say what actually moves the colour.",
         fr_txt="Decris ce qui se passe quand un cristal de permanganate de potassium tombe dans de l'eau immobile. "
                "Dis ce qui deplace vraiment la couleur.",
         sol="Ex. 6 - La couleur s'etale doucement de proche en proche ; les molecules d'eau bousculent les particules de colorant et les emportent (diffusion)."),
]


# ------------------------------------- Chimie AL : concentration molaire
MOLAR = [
    dict(en="Exercise 1 - Read the roles",
         en_txt="Water + salt removed in a beaker: name the solute and the solvent.",
         fr_txt="Eau + sel dissous dans un becher : nomme le solute et le solvant.",
         sol="Ex. 1 - Soluté : le sel ; solvant : l'eau."),
    dict(en="Exercise 2 - Grams to moles",
         en_txt="Convert 5.85 g of NaCl into moles (M = 58.5 g/mol).",
         fr_txt="Convertis 5,85 g de NaCl en moles (M = 58,5 g/mol).",
         sol="Ex. 2 - n = m / M = 5,85 / 58,5 = 0,1 mol."),
    dict(en="Exercise 3 - A saline stock",
         en_txt="0.2 mol of NaCl is made up to 0.25 L. Compute the molarity.",
         fr_txt="0,2 mol de NaCl est complété à 0,25 L. Calcule la molarité.",
         sol="Ex. 3 - c = n / V = 0,2 / 0,25 = 0,8 mol/L."),
    dict(en="Exercise 4 - From a bottle's label",
         en_txt="A bottle reads 2.0 mol/L HCl. How many moles stand inside a 25 mL portion?",
         fr_txt="Un flacon indique 2,0 mol/L de HCl. Combien de moles y a-t-il dans 25 mL ?",
         sol="Ex. 4 - 25 mL = 0,025 L. n = c x V = 2,0 x 0,025 = 0,05 mol (50 mmol)."),
    dict(en="Exercise 5 - Dilute to order",
         en_txt="Take 10 mL of a 2 mol/L stock and add water up to 100 mL. What is the new concentration?",
         fr_txt="On prend 10 mL d'un stock a 2 mol/L et on complete a 100 mL avec de l'eau. Quelle est la nouvelle concentration ?",
         sol="Ex. 5 - C1V1 = C2V2 : 2 x 10 = C2 x 100, donc C2 = 0,2 mol/L."),
    dict(en="Exercise 6 - All in one",
         en_txt="Dissolve 4 g of NaOH (M = 40 g/mol) and top up to 500 mL. "
                "Give the molarity of the final solution step by step.",
         fr_txt="On dissout 4 g de NaOH (M = 40 g/mol) et on complete a 500 mL. "
                "Donne la molarite de la solution finale, etape par etape.",
         sol="Ex. 6 - n = 4 / 40 = 0,1 mol ; V = 0,500 L ; c = 0,1 / 0,500 = 0,2 mol/L."),
]


if __name__ == '__main__':
    build('molar-exercices.pdf', 'Molar Concentration - Practice worksheet',
          'GCE Advanced Level Chemistry - Concentration molaire', MOLAR, with_solutions=False)
    build('molar-corrige.pdf', 'Molar Concentration - Answer key',
          'GCE Advanced Level Chemistry - Concentration molaire - Corrige', MOLAR, with_solutions=True)
    build('diffusion-exercices.pdf', 'Diffusion - Practice worksheet',
          'GCE Ordinary Level Chemistry - La diffusion', DIFFUSION, with_solutions=False)
    build('diffusion-corrige.pdf', 'Diffusion - Answer key',
          'GCE Ordinary Level Chemistry - La diffusion - Corrige', DIFFUSION, with_solutions=True)
    build('atoms-exercices.pdf', 'Atoms, Elements and Compounds - Practice worksheet',
          'GCE Ordinary Level Chemistry - Atomes, elements et composes', ATOMS, with_solutions=False)
    build('atoms-corrige.pdf', 'Atoms, Elements and Compounds - Answer key',
          'GCE Ordinary Level Chemistry - Atomes, elements et composes - Corrige', ATOMS, with_solutions=True)
    build('forces-friction-exercices.pdf', 'Friction and Resultant Forces - Practice worksheet',
          'GCE Ordinary Level Physics - Frottements et resultantes', FRICTION, with_solutions=False)
    build('forces-friction-corrige.pdf', 'Friction and Resultant Forces - Answer key',
          'GCE Ordinary Level Physics - Frottements et resultantes - Corrige', FRICTION, with_solutions=True)
    build('speed-motion-exercices.pdf', 'Speed and Motion - Practice worksheet',
          'GCE Ordinary Level Physics - Vitesse et mouvement', SPEED['exos'], with_solutions=False)
    build('speed-motion-corrige.pdf', 'Speed and Motion - Answer key',
          'GCE Ordinary Level Physics - Vitesse et mouvement - Corrige', SPEED['exos'], with_solutions=True)
    build('acceleration-exercices.pdf', 'Acceleration - Practice worksheet',
          'GCE Ordinary Level Physics - L acceleration', ACCEL, with_solutions=False)
    build('acceleration-corrige.pdf', 'Acceleration - Answer key',
          'GCE Ordinary Level Physics - L acceleration - Corrige', ACCEL, with_solutions=True)
    build('forces-exercices.pdf', 'Forces, Weight and Mass - Practice worksheet',
          'GCE Ordinary Level Physics - Forces et poids', FORCES, with_solutions=False)
    build('forces-corrige.pdf', 'Forces, Weight and Mass - Answer key',
          'GCE Ordinary Level Physics - Forces et poids - Corrige', FORCES, with_solutions=True)
