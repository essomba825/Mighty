"""Correction des exercices.

Chaque type d'exercice a sa regle. Le principe pedagogique applique est
uniforme : une mauvaise reponse n'est jamais punie, elle renvoie vers
l'explication et l'exercice reste reessayable.
"""
import re

from .models import Question


def _norm(value):
    return ' '.join(str(value).split()).strip().lower()


# L'eleve tape « 2 x 2 x 3 x 7 », « 2²×3×7 » ou « 2^2*3*7 » : on normalise
# pour accepter les ecritures reelles plutot qu'une seule forme attendue.
_SUPERSCRIPTS = {
    '\u00b9': '1', '\u00b2': '2', '\u00b3': '3', '\u2074': '4', '\u2075': '5',
    '\u2076': '6', '\u2077': '7', '\u2078': '8', '\u2079': '9', '\u2070': '0',
}
_MULTIPLY = {
    '\u00d7': '*', '\u00b7': '*', '\u2217': '*', '\u2219': '*', '\u00b0': '*',
}


def _norm_math(value):
    text = _norm(value)
    for src, dst in _SUPERSCRIPTS.items():
        text = text.replace(src, '^' + dst)
    for src, dst in _MULTIPLY.items():
        text = text.replace(src, dst)
    return text.replace(' ', '')


def _signature(value):
    """Empreinte numerique d'une ecriture mathematique.

    Permet d'accepter « 4x3x7 », « 4 x 3 x 7 » ou « 2 2 3 7 » pour la meme
    reponse que « 4*3*7 » : on compare les seuls chiffres, dans l'ordre.
    """
    return ''.join(ch for ch in _norm_math(value) if ch.isdigit())


# Un produit est commutatif : « 7*3*2*2 » vaut « 2*2*3*7 ». On ne compare donc
# les chiffres comme un ensemble que si la reponse attendue est bien un produit
# (pas une somme, pas une suite ordonnee).
_PRODUCT_ONLY = re.compile(r'^[\d*^x\u00d7\u00b7]+$')


def _multiset(value):
    return ''.join(sorted(_signature(value)))


def _as_float(value):
    try:
        return float(str(value).replace(',', '.').strip())
    except (TypeError, ValueError):
        return None


def _grade_mcq(question, given):
    choice_id = given.get('choice_id') or given.get('value')
    if choice_id is None:
        return False
    correct = question.choices.filter(is_correct=True).first()
    return correct is not None and str(correct.id) == str(choice_id)


def _grade_numeric(question, given):
    config = question.config or {}
    accepted = config.get('accepted') or []
    tolerance = config.get('tolerance')
    answer = _as_float(given.get('value'))
    if answer is None:
        return False
    for target in accepted:
        expected = _as_float(target)
        if expected is None:
            continue
        if tolerance is not None and abs(answer - expected) <= float(tolerance):
            return True
        if abs(answer - expected) < 1e-9:
            return True
    return False


def _grade_text(question, given):
    config = question.config or {}
    accepted = config.get('accepted') or []
    case_sensitive = bool(config.get('case_sensitive'))
    answer = given.get('value')
    if answer is None:
        return False
    if case_sensitive:
        left, rights = str(answer), [str(w) for w in accepted]
    else:
        left = _norm_math(answer)
        rights = [_norm_math(w) for w in accepted]
    if left in rights:
        return True
    fingerprint = _signature(left)
    if not fingerprint:
        return False
    if fingerprint in {_signature(w) for w in rights}:
        return True
    if all(_PRODUCT_ONLY.match(w) for w in rights):
        return _multiset(left) in {_multiset(w) for w in rights}
    return False


def _grade_ordered(question, given):
    config = question.config or {}
    expected = [str(x) for x in (config.get('items') or [])]
    got = [str(x) for x in (given.get('order') or [])]
    if not expected or len(expected) != len(got):
        return False
    return expected == got


def _grade_pairing(question, given):
    config = question.config or {}
    expected = {str(a): str(b) for a, b in (config.get('pairs') or [])}
    got_pairs = given.get('pairs') or []
    if not expected or len(got_pairs) != len(expected):
        return False
    got = {str(a): str(b) for a, b in got_pairs}
    return got == expected


GRADERS = {
    Question.Kind.MCQ: _grade_mcq,
    Question.Kind.NUMERIC: _grade_numeric,
    Question.Kind.TEXT: _grade_text,
    Question.Kind.ORDERED: _grade_ordered,
    Question.Kind.PAIRING: _grade_pairing,
}


def grade(question, given):
    """Retourne True/False pour la reponse `given` sur `question`."""
    grader = GRADERS.get(question.kind, _grade_mcq)
    return bool(grader(question, given or {}))


def empty_given(question):
    """Reponse vide du bon type, pour initialiser le formulaire eleve."""
    if question.kind == Question.Kind.MCQ:
        return {'choice_id': None}
    if question.kind == Question.Kind.PAIRING:
        return {'pairs': []}
    if question.kind == Question.Kind.ORDERED:
        return {'order': []}
    return {'value': ''}
