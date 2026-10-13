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


if __name__ == '__main__':
    build('speed-motion-exercices.pdf', 'Speed and Motion - Practice worksheet',
          'GCE Ordinary Level Physics - Vitesse et mouvement', SPEED['exos'], with_solutions=False)
    build('speed-motion-corrige.pdf', 'Speed and Motion - Answer key',
          'GCE Ordinary Level Physics - Vitesse et mouvement - Corrige', SPEED['exos'], with_solutions=True)
    build('acceleration-exercices.pdf', 'Acceleration - Practice worksheet',
          'GCE Ordinary Level Physics - L acceleration', ACCEL, with_solutions=False)
    build('acceleration-corrige.pdf', 'Acceleration - Answer key',
          'GCE Ordinary Level Physics - L acceleration - Corrige', ACCEL, with_solutions=True)
