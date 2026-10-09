"""Repetition espacee au niveau question (boites de Leitner).

Le repo contient bien `ConceptState`, mais il est adosse aux `Concept`, et il
n'y a aujourd'hui qu'un seul `Concept` en base : un ecran de revision qui
s'appuierait dessus serait quasi vide. On part donc des `ExerciseAttempt`,
qui sont la seule source fiable, question par question.

Regles :
- boite = nombre de succes consecutifs recents sur cette question, plafonne a
  `len(INTERVALS) - 1`. Un echec la remet a zero.
- une question est a revoir quand sa derniere tentative est un echec, ou quand
  le nombre de jours ecoules depuis son dernier succes depasse
  `INTERVALS[boite]`.
- la review s'arrete au premier exercice de la liste, l'eleve n'est pas noye.
"""
from django.utils import timezone

from .models import ExerciseAttempt, Question

INTERVALS = [1, 2, 4, 8, 16]
MAX_BOX = len(INTERVALS) - 1


def question_box(recent_correct):
    """Boite Leitner = nombre de succes consecutifs en fin de liste.
    On lit la liste du plus recent au plus ancien."""
    box = 0
    for ok in recent_correct:
        if ok:
            box += 1
        else:
            break
    return min(box, MAX_BOX)


def due_questions(student, today=None):
    """Retourne la queue de revision :
    [ (question, box, overdue_days, is_retry), ... ]
    triee par priorite : les echecs d'abord, puis les plus en retard.
    """
    if today is None:
        today = timezone.localdate()

    # Derniere tentative par question, et sequence de succes recents
    from django.db.models import Count, Max, Min
    per_q = {}
    for row in (ExerciseAttempt.objects
                .filter(student=student)
                .order_by('question_id', 'created_at')
                .values('question_id', 'is_correct', 'created_at')):
        qid = row['question_id']
        entry = per_q.setdefault(qid, {'latest': None, 'recent': []})
        entry['latest'] = row
        entry['recent'].append(row['is_correct'])
        if len(entry['recent']) > 5:
            entry['recent'].pop(0)

    due = []
    for qid, state in per_q.items():
        try:
            question = Question.objects.select_related(
                'step__lesson', 'quiz__lesson').get(pk=qid)
        except Question.DoesNotExist:
            continue
        latest = state['latest']
        if not latest['is_correct']:
            # dernier echec : a refaire tout de suite
            due.append((question, 0, (today - latest['created_at'].date()).days, True))
            continue
        box = question_box(list(reversed(state['recent'])))
        interval = INTERVALS[box]
        elapsed = (today - latest['created_at'].date()).days
        if elapsed >= interval:
            due.append((question, box, elapsed - interval, False))

    # trier : echec d'abord, puis plus en retard (plus grande valeur de overdue)
    due.sort(key=lambda item: (not item[3], -item[2]))
    return due
