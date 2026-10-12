# Genere la fiche d'exercices + le corrige de la lecon "Speed and Motion".
# Usage : ..\venv\Scripts\python.exe education/content/gen_speed_motion_pdfs.py
# Les fichiers tombent dans media/resources/ (servis par nginx en production).
import os

from fpdf import FPDF

OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'media', 'resources')
os.makedirs(OUT, exist_ok=True)

PRIMARY = (16, 30, 60)      # navy
ACCENT = (201, 162, 39)     # gold
SOFT = (90, 100, 112)


class Doc(FPDF):
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
        self.set_text_color(*SOFT)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 6, 'Mega Mighty Sixers - contenu original, diffusion libre aux membres de l association',
                  align='C', new_x='RIGHT', new_y='TOP')

    def rule(self, txt):
        self.ln(1)
        self.set_text_color(*PRIMARY)
        self.set_font('helvetica', 'B', 11)
        self.multi_cell(0, 6, txt, new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(2)
        self.set_text_color(30, 34, 42)
        self.set_font('helvetica', '', 10.5)

    def body(self, txt, indent=0):
        self.set_text_color(30, 34, 42)
        self.set_font('helvetica', '', 10.5)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 5.4, txt, new_x='LMARGIN', new_y='NEXT')

    def small(self, txt):
        self.set_text_color(*SOFT)
        self.set_font('helvetica', 'I', 9)
        self.set_x(self.l_margin)
        self.multi_cell(0, 4.8, txt, new_x='LMARGIN', new_y='NEXT')


EXOS = [
    ("Exercise 1 - Average speed",
     "A van covers 150 km in 2 h 30 min on the Yaounde-Bafoussam road. "
     "Compute its average speed in km/h, then in m/s.",
     "Exercice 1 - Vitesse moyenne",
     "Un bus parcourt 150 km en 2 h 30 sur la route Yaounde-Bafoussam. "
     "Calcule sa vitesse moyenne en km/h, puis en m/s."),
    ("Exercise 2 - Unit conversion",
     "Convert 25 m/s into km/h.",
     "Exercice 2 - Conversion d'unites",
     "Convertis 25 m/s en km/h."),
    ("Exercise 3 - Unit conversion, the other way",
     "Convert 108 km/h into m/s.",
     "Exercice 3 - Conversion inverse",
     "Convertis 108 km/h en m/s."),
    ("Exercise 4 - From the graph",
     "A cyclist moves with a constant speed of 8 m/s during 50 s. "
     "What distance does he cover?",
     "Exercice 4 - Lecture du graphe",
     "Un cycliste roule a vitesse constante de 8 m/s pendant 50 s. "
     "Quelle distance parcourt-il ?"),
    ("Exercise 5 - Uniform or not?",
     "A runner's speed stays at 5 m/s for 200 m, then drops to 3 m/s "
     "for the last 100 m. Is the whole motion uniform? Justify.",
     "Exercice 5 - Uniforme ou non ?",
     "La vitesse d'un coureur vaut 5 m/s sur 200 m, puis tombe a 3 m/s "
     "sur les derniers 100 m. Le mouvement complet est-il uniforme ? Justifie."),
    ("Exercise 6 - Average over a journey",
     "A car drives 60 km in 1 h, then 120 km in 1 h. "
     "Compute the average speed over the whole journey. "
     "Is it the mean of the two speeds?",
     u"Exercice 6 - Moyenne sur un trajet",
     u"Une voiture parcourt 60 km en 1 h, puis 120 km en 1 h. "
     u"Calcule la vitesse moyenne sur tout le trajet. "
     u"Est-ce la moyenne des deux vitesses ?"),
]

SOLUTIONS = [
    "Ex. 1 - 2 h 30 = 2,5 h. v = 150 / 2,5 = 60 km/h. En m/s : 60 x 1000 / 3600 = 16,7 m/s environ.",
    "Ex. 2 - 1 m/s = 3,6 km/h, donc 25 x 3,6 = 90 km/h.",
    "Ex. 3 - On divise par 3,6 : 108 / 3,6 = 30 m/s.",
    "Ex. 4 - Mouvement uniforme : d = v x t = 8 x 50 = 400 m.",
    "Ex. 5 - Non : la vitesse change (5 m/s puis 3 m/s). Le mouvement n'est uniforme que si la vitesse reste constante.",
    "Ex. 6 - v_moyenne = distance totale / temps total = (60 + 120) / (1 + 1) = 90 km/h. "
    "La moyenne des vitesses donne aussi 90 km/h, mais seulement parce que les durees sont egales ; "
    "en general il faut toujours diviser la distance totale par le temps total.",
]


def build(path, title, subtitle, with_solutions):
    pdf = Doc(title, subtitle)
    pdf.add_page()
    if not with_solutions:
        pdf.body("Complete each exercise on paper. Write every step of your reasoning, "
                 "then compare with the answer key (separate document).")
        pdf.small("Fais chaque exercice sur une feuille en detaillant ton raisonnement, "
                  "puis compare avec le corrige (document separe).")
        pdf.ln(4)
    n = 0
    for ex_en, ex_en_txt, ex_fr, ex_fr_txt in EXOS:
        n += 1
        pdf.rule(f"{n}. {ex_en}")
        pdf.body(ex_en_txt)
        pdf.body(ex_fr_txt)
        if with_solutions:
            pdf.ln(1)
            pdf.rule("Corrige / Answer")
            pdf.body(SOLUTIONS[n - 1])
        pdf.ln(3)
    pdf.output(os.path.join(OUT, path))
    print('ecrit:', os.path.join(OUT, path))


build('speed-motion-exercices.pdf', 'Speed and Motion - Practice worksheet',
      'GCE Ordinary Level Physics - Vitesse et mouvement', with_solutions=False)
build('speed-motion-corrige.pdf', 'Speed and Motion - Answer key',
      'GCE Ordinary Level Physics - Vitesse et mouvement - Corrige', with_solutions=True)
