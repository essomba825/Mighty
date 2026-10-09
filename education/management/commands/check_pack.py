"""Controle un pack de lecon AVANT toute ecriture en base.

Usage :
    python manage.py check_pack education/content/lesson_18_estimation.json
    python manage.py check_pack <fichier> --quiet

Pourquoi une commande separee, alors que `author_lesson` verifie deja :

`author_lesson` controle le JSON, puis ecrit, puis annule la transaction si la
qualite echoue. C'est sur, mais reversible seulement au prix d'une transaction
annulee, et le fichier reste fautif. Ici on controle le FICHIER, sans ecrire
rien : le defaut se voit avant de toucher la base, et la correction se fait sur
la source, ce qui reste la seule maniere d'empecher le contenu de revenir.

On n'invente pas les regles : on importe `looks_french`, `looks_english` et la
conversion reelle des reponses de `education.grading`. Le controle est donc
celui du serveur, pas une approximation. Ce que l'on ajoute, c'est ce que le
validateur ne fait pas encore :

- la longueur des etapes, comptee par langue ;
- la convertibilite reelle de chaque entree de `numeric.accepted` ;
- le nombre de questions de quiz ;
- la parite `objectives` / `objectives_fr`.
"""
import json
import re

from django.core.management.base import BaseCommand, CommandError

from education.content_quality import looks_english, looks_french
from education.grading import _as_float

MIN_MOTS = 60
MAX_MOTS = 150
TITRE_MAX = 200


def _mots(texte):
    return len(re.findall(r"[a-zA-ZÀ-ÿ0-9']+", texte or ''))


class Command(BaseCommand):
    help = "Controle un pack de lecon sans ecrire en base"

    def add_arguments(self, parser):
        parser.add_argument('content', help='Fichier JSON de la lecon')
        parser.add_argument('--quiet', action='store_true',
                            help='N affiche que le verdict')

    def handle(self, *args, **options):
        try:
            with open(options['content'], encoding='utf-8') as f:
                pack = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f'Fichier introuvable : {options["content"]}'
                               ) from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f'JSON invalide : {exc}') from exc

        if not isinstance(pack, dict):
            raise CommandError('Le pack doit etre un objet JSON.')

        erreurs = []
        avertissements = []

        def bilingue(label, en, fr, obligatoire=True):
            # Un champ optionnel absent n'est pas un defaut : il ne doit pas
            # etre signale. Ce qui est un defaut, c'est d'avoir une version
            # sans l'autre.
            if not en and not fr:
                if obligatoire:
                    erreurs.append(f'{label} : absent dans les deux versions')
                return
            if not en:
                erreurs.append(f'{label} : version anglaise manquante')
                return
            if not fr:
                if obligatoire:
                    erreurs.append(f'{label} : version francaise manquante')
                else:
                    avertissements.append(f'{label} : pas de version francaise')
                return
            if looks_french(en):
                erreurs.append(f'{label} : anglais marque comme francais '
                               f'({en[:60]!r})')
            if looks_english(fr):
                erreurs.append(f'{label} : francais marque comme anglais '
                               f'({fr[:60]!r})')

        champs = pack.get('lesson_fields') or {}
        bilingue('lecon.title', champs.get('title'), champs.get('title_fr'))
        bilingue('lecon.summary', champs.get('summary'), champs.get('summary_fr'),
                 obligatoire=False)
        bilingue('lecon.content', champs.get('content'), champs.get('content_fr'),
                 obligatoire=False)

        obj_en = champs.get('objectives') or []
        obj_fr = champs.get('objectives_fr') or []
        if not obj_en:
            avertissements.append('lecon : pas d\'objectifs')
        elif len(obj_en) != len(obj_fr):
            erreurs.append(f'lecon : {len(obj_en)} objectifs EN mais '
                           f'{len(obj_fr)} FR')
        else:
            for i, (a, b) in enumerate(zip(obj_en, obj_fr), start=1):
                bilingue(f'lecon.objectif{i}', a, b, obligatoire=False)

        etapes = pack.get('steps') or []
        if not etapes:
            erreurs.append('aucune micro-etape dans le fichier')
        if etapes and not any(s.get('required') for s in etapes):
            erreurs.append('aucune etape obligatoire : la lecon ne peut jamais '
                           'etre validee')

        for i, s in enumerate(etapes, start=1):
            titre = (s.get('title') or '').strip()
            if not titre:
                erreurs.append(f'etape{i} : titre manquant')
            elif len(titre) > TITRE_MAX:
                erreurs.append(f'etape{i}.title : {len(titre)} caracteres, sera '
                               f'tronque a {TITRE_MAX}')
            bilingue(f'etape{i}.title', titre, s.get('title_fr'))
            bilingue(f'etape{i}.content', s.get('content'), s.get('content_fr'))
            for langue, valeur in (('EN', s.get('content')),
                                   ('FR', s.get('content_fr'))):
                n = _mots(valeur)
                if valeur and not MIN_MOTS <= n <= MAX_MOTS:
                    erreurs.append(f'etape{i}.content {langue} : {n} mots, hors '
                                   f'{MIN_MOTS}-{MAX_MOTS}')
            q = s.get('question')
            if q:
                self._question(q, f'etape{i}', erreurs, avertissements,
                               bilingue)
            # Invariant de jouabilite, et non de style.
            #
            # Le lecteur ne marque une etape « resolue » que si l'eleve a
            # reussi une question ET que l'etape en contient une
            # (`solved` vaut False sinon). Or il deverrouille l'etape suivante
            # uniquement quand toutes les etapes requises precedentes sont
            # resolues. Consequence : une etape requise SANS question ne peut
            # jamais etre resolue, donc l'etape suivante reste verrouillee pour
            # toujours. L'eleve se bloque sur place, sans message.
            #
            # Les 14 lecons publiees ont 100 % de leurs etapes requises
            # questionnees. Cette regle doit donc etre automatique, sinon le
            # premier pack qui l'ignore produit une lecon injouable.
            if s.get('required') and not q:
                erreurs.append(
                    f'etape{i} : requise mais SANS question — le lecteur ne '
                    f'pourra jamais la marquer resolue, donc les etapes '
                    f'suivantes resteront verrouillees (lecon injouable). '
                    f'Mets la question dans l\'etape, ou required=false')

        quiz = pack.get('quiz') or {}
        bilingue('quiz.title', quiz.get('title'), quiz.get('title_fr'),
                 obligatoire=False)
        questions = quiz.get('questions') or []
        if len(questions) < 4:
            erreurs.append(f'quiz : {len(questions)} questions, 4 minimum')
        for i, q in enumerate(questions, start=1):
            self._question(q, f'quiz{i}', erreurs, avertissements, bilingue)

        if not options['quiet']:
            self.stdout.write(f'{len(etapes)} etape(s), '
                              f'{len(questions)} question(s) de quiz')

        for message in erreurs:
            self.stdout.write(self.style.ERROR(f'  ERREUR  {message}'))
        for message in avertissements:
            self.stdout.write(self.style.WARNING(f'  avertis. {message}'))

        if erreurs:
            self.stdout.write(self.style.ERROR(
                f'CONTROLE DU PACK : {len(erreurs)} erreur(s) — rien n\'a ete '
                f'ecrit. Corrige le fichier.'))
            raise CommandError('pack refuse')
        self.stdout.write(self.style.SUCCESS(
            f'CONTROLE DU PACK : OK ({len(avertissements)} avertissement(s))'))

    def _question(self, q, prefixe, erreurs, avertissements, bilingue):
        bilingue(f'{prefixe}.text', q.get('text'), q.get('text_fr'))
        bilingue(f'{prefixe}.explication', q.get('explanation'),
                 q.get('explanation_fr'), obligatoire=False)
        bilingue(f'{prefixe}.indice.invite', q.get('hint_prompt'),
                 q.get('hint_prompt_fr'), obligatoire=False)

        kind = q.get('kind', 'mcq')
        config = q.get('config') or {}

        # Meme raison que pour `numeric.accepted` : `author_lesson` fait
        # `int(difficulty)`, et une etiquette comme "easy" leve un ValueError
        # au moment d'ECRIRE. Le control du fichier passait, puis la lecon
        # etait refusee sur une traceback au lieu d'un message. On verifie donc
        # ici la convertibilite reelle, pas la presence du champ.
        if 'difficulty' in q:
            try:
                int(q['difficulty'])
            except (TypeError, ValueError):
                erreurs.append(
                    f'{prefixe} : difficulty {q["difficulty"]!r} n\'est pas un '
                    f'entier — `author_lesson` fait int(difficulty) et leve une '
                    f'ValueError a l\'ecriture. Utilise 1, 2 ou 3')

        if kind == 'mcq':
            choix = q.get('choices') or []
            if len(choix) < 2:
                erreurs.append(f'{prefixe} : QCM avec moins de 2 choix')
            corrects = [c for c in choix if c.get('correct')]
            if len(corrects) != 1:
                erreurs.append(f'{prefixe} : {len(corrects)} bonne(s) reponse(s), '
                               f'1 attendue')
            for i, c in enumerate(choix, start=1):
                bilingue(f'{prefixe}.choix{i}', c.get('text'), c.get('text_fr'),
                         obligatoire=False)
            libelles = [c.get('text') for c in choix]
            if len(libelles) != len(set(libelles)):
                erreurs.append(f'{prefixe} : libelles de choix en double')

        elif kind == 'numeric':
            self._accepted(q, prefixe, config, erreurs, numerique=True)
        elif kind == 'text':
            self._accepted(q, prefixe, config, erreurs, numerique=False)
        elif kind == 'ordered':
            if len(config.get('items') or []) < 2:
                erreurs.append(f'{prefixe} : config ordre sans 2 elements')
            if not (config.get('items_fr') or []):
                avertissements.append(f'{prefixe} : pas de version francaise '
                                      f'des elements')
        elif kind == 'pairing':
            paires = config.get('pairs') or []
            if not paires:
                erreurs.append(f'{prefixe} : config appariement sans pairs')
            for a, b in paires:
                if a == b:
                    erreurs.append(f'{prefixe} : paire triviale {a!r}')
            if not (config.get('pairs_fr') or []):
                avertissements.append(f'{prefixe} : pas de version francaise '
                                      f'des paires')

    def _accepted(self, q, prefixe, config, erreurs, *, numerique):
        accepted = config.get('accepted')
        if not isinstance(accepted, list) or not accepted:
            erreurs.append(f'{prefixe} : config sans "accepted" non vide')
            return
        for valeur in accepted:
            if numerique:
                # La faute la plus discrete du projet : une entree non
                # convertible est ignoree par le correcteur, sans message. Si
                # c'est la seule, l'exercice devient impossible a reussir.
                if _as_float(valeur) is None:
                    erreurs.append(
                        f'{prefixe} : {valeur!r} dans accepted n\'est pas '
                        f'convertible en nombre — le correcteur l\'ignore et '
                        f'l\'exercice devient impossible a reussir')
            elif not isinstance(valeur, str):
                erreurs.append(f'{prefixe} : {valeur!r} n\'est pas une chaine '
                               f'pour un exercice de type text')