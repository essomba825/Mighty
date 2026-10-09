"""Regles de qualite du contenu pedagogique.

Utilise par deux commandes :
  - `author_lesson` refuse d'ecrire une lecon qui viole une regle bloquante ;
  - `check_content` audite l'ensemble de la base et rend compte.

Les regles sont volontairement severes : un contenu pedagogique faux ou
vide est plus pire qu'une lecon absente, parce qu'il donne une fausse
reassurance a l'eleve.
"""
import re

# Mots outils du francais. Volontairement restreint : les mots hachees qui
# existent aussi en anglais ("fraction", "question", "nombre", "erreur") sont
# exclus, sinon un titre anglais legitimate declenche un faux positif.
FRENCH_MARKERS = re.compile(
    # « on » est volontairement absent : c'est un pronom tres courant en
    # francais, mais l'anglais l'emploie tout autant ("x on both sides"), et
    # le confondre faisait rejeter des titres anglais legitimes.
    r"\b(le|la|les|un|une|des|du|de|et|est|sont|il|elle|ne|pas|"
    r"que|qui|quoi|comment|pourquoi|combien|quel|quelle|parmi|entre|"
    r"avec|sans|mais|donc|car|tout|tous|toute|toutes|son|sa|ses|"
    r"leur|nos|vos|ce|cet|ces|mon|ma|mes|ton|ta|tes|"
    r"diviseur|diviseurs|premiere|premieres|lecon|leçons|"
    r"reponse|réponse|réponses|indice|indices|"
    r"comprehension|compréhension|aujourd'hui|lorsque|puisque|"
    r"beaucoup|petit|grand|trouve|calcule|ecris|écris|reconnais)\b",
    re.IGNORECASE)

ENGLISH_MARKERS = re.compile(
    r"\b(the|and|which|what|how|why|whose|whom|when|where|with|without|"
    r"from|into|this|that|these|those|there|their|they|them|its|it|"
    r"is|are|was|were|be|been|being|do|does|did|have|has|had|"
    r"not|but|for|about|because|answer|answers|question|questions|"
    r"number|numbers|prime|divisor|divisors|factor|factors|"
    r"integer|integers|lesson|lessons|example|examples|error|errors|"
    r"hint|hints|write|find|calculate|compute|which of|out of|"
    r"how many|remember|common|wrong|right|correct|incorrect)\b",
    re.IGNORECASE)

# Un texte francais court comme "Parmi ces nombres" ne contient presque que
# des mots outils : on exige un ratio avant de crier au melange, sinon chaque
# titre d'une etape declenche un faux positif.
FRENCH_RATIO = 0.22
ENGLISH_RATIO = 0.22


def looks_french(text):
    """True si le texte est majoritairement francais."""
    words = re.findall(r"[a-zA-ZÀ-ÿ']+", text or '')
    if len(words) < 4:
        return False
    hits = sum(1 for w in words if FRENCH_MARKERS.fullmatch(w))
    return hits / len(words) >= FRENCH_RATIO


def looks_english(text):
    """True si le texte est majoritairement anglais."""
    words = re.findall(r"[a-zA-ZÀ-ÿ']+", text or '')
    if len(words) < 4:
        return False
    hits = sum(1 for w in words if ENGLISH_MARKERS.fullmatch(w))
    return hits / len(words) >= ENGLISH_RATIO


def check_translation_pair(label, en, fr, errors, warnings,
                           min_words=4, required=True):
    """Verifie qu'un couple EN/FR est coherent.

    `errors`   : problemes qui interdisent la publication.
    `warnings` : problemes a corriger mais non bloquants.
    """
    if not en:
        errors.append(f'{label} : version anglaise vide')
        return
    if not fr:
        if required:
            errors.append(f'{label} : version francaise manquante')
        else:
            warnings.append(f'{label} : pas de version francaise (repli EN)')
        return
    # Un choix purement numerique ("12", "3 x 5") est legitimately identique
    # dans les deux langues : on ne signale que les vraies phrases.
    identique = fr.strip() == en.strip()
    if identique and looks_english(en):
        warnings.append(f'{label} : version francaise identique a l\'anglaise')
    if looks_french(en):
        errors.append(f'{label} : le texte anglais contient du francais '
                      f'({en[:60]!r})')
    if looks_english(fr):
        errors.append(f'{label} : le texte francais contient de l\'anglais '
                      f'({fr[:60]!r})')


def check_question(question, errors, warnings, quiz=False):
    """Verifie la correction d'un exercice. `quiz=True` pour un bilan de fin
    de lecon, `False` pour une verification d'etape."""
    prefix = f'{"quiz" if quiz else "etape"} Q{question.id or "?"}'

    check_translation_pair(f'{prefix}.text', question.text, question.text_fr,
                           errors, warnings)
    check_translation_pair(f'{prefix}.explication', question.explanation,
                           question.explanation_fr, errors, warnings,
                           required=False)

    kind = question.kind
    config = question.config or {}
    choices = list(question.choices.all())

    if kind == 'mcq':
        if len(choices) < 2:
            errors.append(f'{prefix} : QCM avec {len(choices)} seul choix')
        corrects = [c for c in choices if c.is_correct]
        if len(corrects) != 1:
            errors.append(f'{prefix} : exactement une bonne reponse attendue, '
                          f'{len(corrects)} trouvee(s)')
        for c in choices:
            check_translation_pair(f'{prefix}.choix{c.id}', c.text, c.text_fr,
                                   errors, warnings, required=False)
        # Comparaison sensible a la casse : « AA », « Aa » et « aa » sont trois
        # alleles differents, et les mettre en minuscules cree un faux positif
        # sur les doubles qui empeche de publier une question de genetique.
        textes = [c.text.strip() for c in choices if c.text]
        if len(textes) != len(set(textes)):
            errors.append(f'{prefix} : choix en double')

    elif kind == 'numeric':
        accepted = config.get('accepted')
        if not isinstance(accepted, list) or not accepted:
            errors.append(f'{prefix} : config numerique sans "accepted"')

    elif kind == 'text':
        accepted = config.get('accepted')
        if not isinstance(accepted, list) or not accepted:
            errors.append(f'{prefix} : config texte sans "accepted"')

    elif kind == 'ordered':
        items = config.get('items')
        if not isinstance(items, list) or len(items) < 2:
            errors.append(f'{prefix} : config ordre sans au moins 2 elements')
        elif len(items) != len(set(map(str, items))):
            errors.append(f'{prefix} : elements a remettre en ordre en double')
        if not (config.get('items_fr') or []):
            warnings.append(f'{prefix} : pas de version francaise des elements')

    elif kind == 'pairing':
        paires = config.get('pairs')
        if not isinstance(paires, list) or not paires:
            errors.append(f'{prefix} : config appariement sans "pairs"')
        else:
            for a, b in paires:
                if a == b:
                    errors.append(f'{prefix} : paire triviale {a!r} == {b!r}')
            if len({a for a, _ in paires}) != len(paires):
                errors.append(f'{prefix} : element de gauche en double')
        if not (config.get('pairs_fr') or []):
            warnings.append(f'{prefix} : pas de version francaise des paires')

    if kind != 'mcq' and choices:
        warnings.append(f'{prefix} : des choix sont defines sur un exercice '
                        f'de type {kind} (ignores)')

    indices = question.hints.order_by('order')
    ordres = [h.order for h in indices]
    if ordres != list(range(1, len(ordres) + 1)):
        warnings.append(f'{prefix} : indices non numerotes a partir de 1')
    for hint in indices:
        check_translation_pair(f'{prefix}.indice{hint.order}', hint.text,
                               hint.text_fr, errors, warnings,
                               required=False)


def check_lesson(lesson, errors, warnings):
    """Verifie une lecon complete : metadonnees, etapes, questions, quiz."""
    tag = f'lecon {lesson.id}'
    check_translation_pair(f'{tag}.title', lesson.title, lesson.title_fr,
                           errors, warnings)

    for nom, en, fr in (('resume', lesson.summary, lesson.summary_fr),):
        if not en and not fr:
            warnings.append(f'{tag} : pas de {nom}')
        else:
            check_translation_pair(f'{tag}.{nom}', en, fr, errors, warnings,
                                   required=False)

    for nom, en, fr in (('objectifs_en', lesson.objectives,
                         lesson.objectives_fr),):
        if not en:
            warnings.append(f'{tag} : pas d\'objectifs d\'apprentissage')
        elif not fr:
            warnings.append(f'{tag} : pas d\'objectifs en francais')
        elif len(en) != len(fr):
            errors.append(f'{tag} : {len(en)} objectifs EN mais {len(fr)} FR')
        else:
            for i, (o_en, o_fr) in enumerate(zip(en, fr), start=1):
                check_translation_pair(f'{tag}.objectif{i}', o_en, o_fr,
                                       errors, warnings, required=False)

    steps = list(lesson.steps.all())
    if not steps:
        # Published lessons remain readable without micro-steps when they carry
        # content or a video: the step player then falls back to the long text.
        # Only a completely empty lesson (nothing to read) is an error.
        has_content = bool(
            (lesson.content or '').strip()
            or (lesson.content_fr or '').strip()
            or (lesson.video_url or '').strip())
        if not has_content:
            errors.append(f'{tag} : aucun contenu — ni etapes, ni texte, ni video')
        else:
            warnings.append(f'{tag} : pas de micro-etapes — la lecon s affiche '
                            f'en long texte')
        return
    if not any(s.required for s in steps):
        warnings.append(f'{tag} : aucune etape obligatoire, la lecon ne peut '
                        f'jamais etre validee')

    for step in steps:
        prefix = f'{tag}.etape{step.order}'
        check_translation_pair(f'{prefix}.title', step.title, step.title_fr,
                               errors, warnings, required=False)
        if not (step.content or step.content_fr):
            errors.append(f'{prefix} : ni contenu anglais ni francais')
        else:
            check_translation_pair(f'{prefix}.content', step.content,
                                   step.content_fr, errors, warnings,
                                   required=False)

    quiz_questions = [q for quiz in lesson.quizzes.all()
                      for q in quiz.questions.all()]
    if not quiz_questions:
        warnings.append(f'{tag} : aucun quiz de fin de lecon')

    for q in quiz_questions:
        check_question(q, errors, warnings, quiz=True)
    for step in steps:
        if step.question:
            check_question(step.question, errors, warnings, quiz=False)
