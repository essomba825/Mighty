# Genere les figures pedagogiques SVG des lecons (vecteur = net a toute taille).
# Usage : ..\venv\Scripts\python.exe education/content/gen_lesson_svgs.py
# Les fichiers tombent dans media/lessons/ (nginx /media/ les sert en prod).
import os

OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'media', 'lessons')
os.makedirs(OUT, exist_ok=True)

NAVY = '#0b2d58'
GOLD = '#c9a227'
GOLD_L = '#f2b84b'
TEAL = '#2e7d6e'
GREEN = '#33691e'
RED = '#a5352a'
INK = '#233449'
SOFT = '#8a97a6'
GRID = '#dbe3ec'
PAPER = '#ffffff'

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 260" '
        'font-family="Segoe UI, Roboto, sans-serif">')


def write(name, body):
    with open(os.path.join(OUT, name + '.svg'), 'w', encoding='utf-8') as f:
        f.write(HEAD + body + '</svg>')
    print('ecrit:', name)


def axes(x0=52, y0=210, x1=372, y1=26, xlabel='time (s)', ylabel='distance (m)'):
    return (
        f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{INK}" stroke-width="2"/>'
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{INK}" stroke-width="2"/>'
        f'<polygon points="{x1},{y0} {x1-9},{y0-5} {x1-9},{y0+5}" fill="{INK}"/>'
        f'<polygon points="{x0},{y1} {x0-5},{y1+9} {x0+5},{y1+9}" fill="{INK}"/>'
        f'<text x="{x1}" y="{y0+24}" text-anchor="end" font-size="13" fill="{INK}">{xlabel}</text>'
        f'<text x="{x0-8}" y="{y1+2}" text-anchor="end" font-size="13" fill="{INK}" '
        f'transform="rotate(-90 {x0-14} {y1+2})" transform="rotate(-90)" >{ylabel}</text>'
    )


# 1) Graphe distance-temps : montee - plateau - montee (un trajet avec pause)
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
for gx in range(102, 373, 50):
    body += f'<line x1="{gx}" y1="34" x2="{gx}" y2="210" stroke="{GRID}" stroke-width="1"/>'
body += axes(xlabel='temps (s)', ylabel='distance (m)')
body += (f'<polyline points="52,210 152,110 232,110 332,52" fill="none" stroke="{NAVY}" '
         f'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
for px, py in ((152, 110), (232, 110), (332, 52)):
    body += f'<circle cx="{px}" cy="{py}" r="5" fill="{GOLD_L}"/>'
body += (f'<line x1="152" y1="210" x2="152" y2="110" stroke="{SOFT}" stroke-dasharray="4 4"/>'
         f'<line x1="232" y1="210" x2="232" y2="110" stroke="{SOFT}" stroke-dasharray="4 4"/>'
         f'<text x="102" y="232" font-size="11" fill="{SOFT}">marche</text>'
         f'<text x="172" y="232" font-size="11" fill="{SOFT}">pause (distance figee)</text>'
         f'<text x="262" y="232" font-size="11" fill="{SOFT}">marche a nouveau</text>')
write('physics-distance-time', body)

# 2) Graphe vitesse-temps : vitesse constante + aire = distance
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
body += axes(xlabel='temps (s)', ylabel='vitesse (m/s)')
X0, Y0 = 52, 210
x2 = 322
y_line = 90
body += (f'<rect x="{X0}" y="{y_line}" width="{x2 - X0}" height="{Y0 - y_line}" '
         f'fill="{GOLD_L}" opacity="0.28"/>')
body += (f'<line x1="{X0}" y1="{y_line}" x2="{x2}" y2="{y_line}" stroke="{NAVY}" '
         f'stroke-width="4" stroke-linecap="round"/>')
body += (f'<text x="{(X0 + x2) / 2}" y="{(Y0 + y_line) / 2}" text-anchor="middle" '
         f'font-size="14" font-weight="700" fill="{NAVY}">aire = distance</text>')
body += (f'<line x1="{X0}" y1="{y_line}" x2="{X0}" y2="{Y0}" stroke="{RED}" stroke-dasharray="4 4"/>'
         f'<text x="{X0 - 6}" y="{y_line - 8}" text-anchor="end" font-size="12" fill="{RED}">v</text>')
write('physics-speed-time', body)

# 3) Acceleration : vitesse-temps triangle (montee/descent)
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
for gx in range(102, 373, 50):
    body += f'<line x1="{gx}" y1="34" x2="{gx}" y2="210" stroke="{GRID}" stroke-width="1"/>'
body += axes(xlabel='temps (s)', ylabel='vitesse (m/s)')
pts = '52,210 172,74 262,74 352,210'
body += (f'<polyline points="{pts}" fill="none" stroke="{NAVY}" stroke-width="4" '
         f'stroke-linecap="round" stroke-linejoin="round"/>')
body += f'<circle cx="172" cy="74" r="5" fill="{GOLD_L}"/><circle cx="262" cy="74" r="5" fill="{GOLD_L}"/>'
body += (f'<text x="92" y="150" font-size="12" font-weight="700" fill="{GREEN}">accelere</text>'
         f'<text x="169" y="66" font-size="12" font-weight="700" fill="{NAVY}">vitesse constante</text>'
         f'<text x="289" y="150" font-size="12" font-weight="700" fill="{RED}">freinage</text>')
write('physics-acceleration', body)

# 4) Bloc pose sur table avec forces : poids, normale, moteur, frottement
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
body += (f'<line x1="40" y1="196" x2="360" y2="196" stroke="{INK}" stroke-width="3"/>')
for i in range(40, 360, 12):
    body += f'<line x1="{i}" y1="198" x2="{i - 8}" y2="210" stroke="{SOFT}" stroke-width="1.4"/>'
body += (f'<rect x="130" y="120" width="120" height="76" rx="10" fill="{NAVY}"/>'
         f'<text x="190" y="163" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">caisse</text>')
arrows = [
    (190, 120, 190, 66, TEAL, 'normale N'),     # haut
    (190, 196, 190, 240, NAVY, 'poids W = m g'),# bas (attention Y grandit vers le bas)
    (250, 158, 320, 158, GREEN, 'moteur'),      # droite
    (130, 158, 62, 158, RED, 'frottement f'),   # gauche
]
for x0, y0, x1, y1, col, lab in arrows:
    body += f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>'
    dx, dy = x1 - x0, y1 - y0
    s = (dx**2 + dy**2) ** 0.5
    ux, uy = dx / s, dy / s
    tip = (x1, y1)
    left = (x1 - ux * 12 - uy * 7, y1 - uy * 12 + ux * 7)
    right = (x1 - ux * 12 + uy * 7, y1 - uy * 12 - ux * 7)
    body += f'<polygon points="{tip[0]},{tip[1]} {left[0]:.0f},{left[1]:.0f} {right[0]:.0f},{right[1]:.0f}" fill="{col}"/>'
    lx = (x0 + x1) / 2
    ly = (y0 + y1) / 2 - 8
    body += f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="12" font-weight="700" fill="{col}">{lab}</text>'
write('physics-forces-block', body)

# 5) Trois etats de la matiere : solide / liquide / gaz (particules)
def particles(cx0, cy0, cols, rows, tight=True):
    out = ''
    for r in range(rows):
        for c in range(cols):
            jitter = 0 if tight else ((r * c * 13) % 9 - 4)
            jy = 0 if tight else ((r * 7 + c * 11) % 7 - 3)
            out += (f'<circle cx="{cx0 + c * 18 + jitter}" cy="{cy0 + r * 18 + jy}" '
                    f'r="7" fill="{NAVY}" stroke="#fff" stroke-width="1.6"/>')
    return out

body = '<rect width="400" height="260" fill="%s"/>' % PAPER
frames = [('solide', 28, True), ('liquide', 154, False), ('gaz', 278, False, True)]
for x0 in (28, 154, 278):
    body += f'<rect x="{x0}" y="42" width="100" height="138" rx="10" fill="none" stroke="{INK}" stroke-width="2.5"/>'
labels = [('solide', 78), ('liquide', 204), ('gaz', 328)]
for label, cx in labels:
    body += f'<text x="{cx}" y="28" text-anchor="middle" font-size="13" font-weight="700" fill="{INK}">{label}</text>'
body += particles(45, 62, 4, 6, True)                  # solide : reseau serre
# liquide : proches mais desordonnees
for r in range(6):
    for c in range(4):
        body += (f'<circle cx="{177 + c * 19 + (9 if r % 2 else 0)}" cy="{70 + r * 18 + (c * 5 + r * 7) % 9 - 4}" '
                 f'r="7" fill="{TEAL}" stroke="#fff" stroke-width="1.6"/>')
# gaz : epars, grandes distances
for cx_, cy_ in ((300, 64), (368, 60), (318, 116), (370, 122), (340, 170), (296, 158)):
    body += f'<circle cx="{cx_}" cy="{cy_}" r="7" fill="{GOLD}" stroke="#fff" stroke-width="1.6"/>'
body += (f'<text x="78" y="224" text-anchor="middle" font-size="10.5" fill="{SOFT}">reseau fixe</text>'
         f'<text x="204" y="224" text-anchor="middle" font-size="10.5" fill="{SOFT}">glisse lentement</text>'
         f'<text x="328" y="224" text-anchor="middle" font-size="10.5" fill="{SOFT}">voyage librement</text>')
write('chem-states-particles', body)

# 6) Atome de Bohr (oxygene) : noyau + 2 couches
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
cx, cy = 200, 130
body += f'<circle cx="{cx}" cy="{cy}" r="24" fill="{NAVY}"/><text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="14" font-weight="700" fill="#fff">8p 8n</text>'
for r in (58, 95):
    body += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GOLD}" stroke-width="2.5"/>'
import math
for r, count in ((58, 2), (95, 6)):
    for k in range(count):
        ang = 2 * math.pi * k / count + (r == 58) * 0.6
        ex = cx + r * math.cos(ang)
        ey = cy + r * math.sin(ang)
        body += (f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="8" fill="{TEAL}" stroke="#fff" stroke-width="2"/>'
                 f'<text x="{ex:.1f}" y="{ey + 4:.1f}" text-anchor="middle" font-size="10" '
                 f'font-weight="700" fill="#fff">e-</text>')
body += (f'<text x="200" y="246" text-anchor="middle" font-size="12.5" fill="{SOFT}">'
         f'oxygene : 8 electrons sur deux couches</text>')
write('chem-atom-bohr', body)

# 7) Verrerie : becher + eprouvette jaugee avec graduations
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
# becher
body += (f'<path d="M 96 44 L 96 190 A 18 18 0 0 0 114 208 L 200 208 A 18 18 0 0 0 218 190 L 218 44" '
         f'fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
body += (f'<rect x="100" y="118" width="114" height="80" fill="{GOLD_L}" opacity=".35"/>'
         f'<line x1="96" y1="118" x2="218" y2="118" stroke="{RED}" stroke-width="2" stroke-dasharray="5 4"/>'
         f'<text x="230" y="122" font-size="12" fill="{RED}">niveau</text>')
for i, yv in enumerate(range(150, 190, 10)):
    body += f'<line x1="96" y1="{yv}" x2="{112}" y2="{yv}" stroke="{INK}" stroke-width="1.4"/>'
body += f'<text x="157" y="240" text-anchor="middle" font-size="12" fill="{SOFT}">becher (volume approximatif)</text>'
# eprouvette
body += (f'<path d="M 300 44 L 300 190 A 14 14 0 0 0 314 204 L 336 204 A 14 14 0 0 0 350 190 L 350 44" '
         f'fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
body += f'<rect x="299" y="96" width="52" height="96" fill="{TEAL}" opacity=".30"/>'
for idx, yv in enumerate(range(60, 200, 20)):
    body += f'<line x1="300" y1="{yv}" x2="{318}" y2="{yv}" stroke="{INK}" stroke-width="1.4"/>'
body += f'<text x="325" y="240" text-anchor="middle" font-size="12" fill="{SOFT}">eprouvette (graduations precises)</text>'
write('chem-glassware', body)

# 8) Carre de Punnett : Aa x Aa
body = '<rect width="400" height="260" fill="%s"/>' % PAPER
ox, oy, cs = 96, 52, 66
body += f'<text x="{ox + cs}" y="{oy - 18}" text-anchor="middle" font-size="20" font-weight="800" fill="{NAVY}">A</text>'
body += f'<text x="{ox + 2.6 * cs}" y="{oy - 18}" text-anchor="middle" font-size="20" font-weight="800" fill="{NAVY}">a</text>'
for k, letter in enumerate(('A', 'a')):
    body += f'<text x="{ox - 18}" y="{oy + cs * k + cs * .68}" text-anchor="middle" font-size="20" font-weight="800" fill="{NAVY}">{letter}</text>'
for i in range(2):
    for j in range(2):
        cx0, cy0 = ox + j * cs, oy + i * cs
        vals = (('AA', 'Aa'), ('Aa', 'aa'))
        body += (f'<rect x="{cx0}" y="{cy0}" width="{cs}" height="{cs}" fill="#f2f6fb" stroke="{INK}" '
                 f'stroke-width="1.6" rx="6"/>'
                 f'<text x="{cx0 + cs / 2}" y="{cy0 + cs / 2 + 9}" text-anchor="middle" font-size="20" '
                 f'font-weight="800" fill="{GOLD}">{vals[i][j]}</text>')
body += (f'<text x="200" y="246" text-anchor="middle" font-size="12.5" fill="{SOFT}">'
         f'Aa x Aa : 25% AA, 50% Aa, 25% aa</text>')
write('bio-punnett', body)

print('OK', len(os.listdir(OUT)), 'figures au total dans media/lessons')
