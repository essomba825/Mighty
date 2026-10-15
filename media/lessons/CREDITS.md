# Crédits des figures — `media/lessons/`

Figures pédagogiques servies aux élèves. Les SVG « maison » (physics-*, chem-*,
bio-*) sont produits par `backend/education/content/gen_lesson_svgs.py`.
Les SVG « math-* » proviennent de Wikimedia Commons et sont réutilisés ici.

## Figures importées de Wikimedia Commons

| Fichier local | Œuvre d'origine | Auteur | Licence |
|---|---|---|---|
| `math-circle-lines.svg` | [CIRCLE LINES-en.svg](https://commons.wikimedia.org/wiki/File:CIRCLE_LINES-en.svg) | Jleedev | Domaine public |
| `math-cuboid.svg` | [Cuboid 01.svg](https://commons.wikimedia.org/wiki/File:Cuboid_01.svg) | Д.Ильин (vectorisation) | CC0 1.0 |
| `math-pythagoras.svg` | [Pythagorean.svg](https://commons.wikimedia.org/wiki/File:Pythagorean.svg) | Wapcaplet (d'après Michael Hardy, Steff, Leo2004) | CC BY-SA 3.0 |
| `math-sohcahtoa.svg` | [Sohcahtoa.svg](https://commons.wikimedia.org/wiki/File:Sohcahtoa.svg) | James Hare | Domaine public |
| `math-mean-median-mode.svg` | [Visualisation mode median mean.svg](https://commons.wikimedia.org/wiki/File:Visualisation_mode_median_mean.svg) | Cmglee | CC BY-SA 3.0 |
| `math-bar-chart.svg` | [Simple bar chart.svg](https://commons.wikimedia.org/wiki/File:Simple_bar_chart.svg) | Masur | Domaine public |
| `math-dice-distribution.svg` | [Dice Distribution (bar).svg](https://commons.wikimedia.org/wiki/File:Dice_Distribution_(bar).svg) | Tim Stellmach | Domaine public |

## Figures importées — Physique / Biologie

| Fichier local | Œuvre d'origine | Auteur | Licence |
|---|---|---|---|
| `physics-energy-pk.svg` | [Energy-p-k-i.svg](https://commons.wikimedia.org/wiki/File:Energy-p-k-i.svg) | KoenB | Domaine public |
| `physics-free-body-2.svg` | [Free body diagram2.svg](https://commons.wikimedia.org/wiki/File:Free_body_diagram2.svg) | Krishnavedala | CC0 1.0 |
| `physics-momentum-collision.svg` | [Collision with mass and velocity.svg](https://commons.wikimedia.org/wiki/File:Collision_with_mass_and_velocity.svg) | Maxmath12 | CC0 1.0 |
| `physics-pressure-force-area.svg` | [Pressure force area.svg](https://commons.wikimedia.org/wiki/File:Pressure_force_area.svg) | Klaus-Dieter Keller | Domaine public |
| `physics-distance-displacement.svg` | [Distancedisplacement.svg](https://commons.wikimedia.org/wiki/File:Distancedisplacement.svg) | User:Stannered | CC BY-SA 3.0 |
| `bio-plant-cell.svg` | [Plant cell structure-en.svg](https://commons.wikimedia.org/wiki/File:Plant_cell_structure-en.svg) | LadyofHats | Domaine public |
| `bio-protein-primary.svg` | [Protein primary structure.svg](https://commons.wikimedia.org/wiki/File:Protein_primary_structure.svg) | National Human Genome Research Institute | Domaine public |
| `bio-enzyme-model.svg` | [Enzyme Model.svg](https://commons.wikimedia.org/wiki/File:Enzyme_Model.svg) | Tenthkrige | CC0 1.0 |
| `bio-osmosis.svg` | [Osmosis diagram.svg](https://commons.wikimedia.org/wiki/File:Osmosis_diagram.svg) | KDS4444 | CC0 1.0 |
| `bio-mitosis.svg` | [Major events in mitosis.svg](https://commons.wikimedia.org/wiki/File:Major_events_in_mitosis.svg) | Mysid | Domaine public |
| `bio-dna.svg` | [DNA simple2.svg](https://commons.wikimedia.org/wiki/File:DNA_simple2.svg) | Forluvoft | Domaine public |

## Où sont utilisées les figures

| Leçon | Étape | Fichier |
|---|---|---|
| 32 Circles | 1 | `math-circle-lines.svg` |
| 33 Solids | 1 | `math-cuboid.svg` |
| 34 Pythagoras | 1 | `math-pythagoras.svg` |
| 35 Trigonometry | 1 | `math-sohcahtoa.svg` |
| 36 Averages | 1 | `math-mean-median-mode.svg` |
| 37 Charts | 1 | `math-bar-chart.svg` |
| 38 Probability | 1 | `math-dice-distribution.svg` |
| 1 Work, Energy and Power | 3 | `physics-energy-pk.svg` |
| 56 Newton's Laws | 1 | `physics-free-body-2.svg` |
| 57 Momentum and Collisions | 1 | `physics-momentum-collision.svg` |
| 58 Density and Pressure | 3 | `physics-pressure-force-area.svg` |
| 59 Distance, Displacement and Units | 1 | `physics-distance-displacement.svg` |
| 66 Cells and Cell Structure | 1 | `bio-plant-cell.svg` |
| 67 Biological Molecules | 3 | `bio-protein-primary.svg` |
| 68 Enzymes | 2 | `bio-enzyme-model.svg` |
| 69 Transport Across Membranes | 3 | `bio-osmosis.svg` |
| 70 Cell Division | 3 | `bio-mitosis.svg` |
| 71 DNA and Protein Synthesis | 1 | `bio-dna.svg` |

### Obligations de licence
- **CC0 / Domaine public** : aucune obligation (crédit fourni par courtoisie).
- **CC BY-SA 3.0** (`math-pythagoras.svg`, `math-mean-median-mode.svg`) :
  attribution obligatoire **et** partage à l'identique. Ces œuvres sont
  reproduites **non modifiées** ; toute adaptation devra être publiée sous
  licence identique. Le crédit auteur est également affiché sous la figure
  dans la leçon concernée.

## Comment récupérer / mettre à jour une figure
L'outil `commons.py` (requêtes API + téléchargement) interroge
`commons.wikimedia.org` via `Special:FilePath`/`imageinfo` et enregistre
auteur + licence. Modèle de requête :

```
action=query&list=search&srsearch=<termes> filetype:drawing&srnamespace=6
action=query&titles=<Fichier>&prop=imageinfo&iiprop=url|size|mime|extmetadata
```
