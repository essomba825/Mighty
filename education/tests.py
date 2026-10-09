"""Tests d'invariants de l'education.

On ne teste pas le rendu : on ecrit les regles qui, si elles regressent,
rendent le produit casse sans que rien ne le dise. Chacune correspond a un
defaut reel rencontre pendant la relecture de la lecon 18.

Une regle non ecrite est une regle qui disparait au prochain contenu authored :
les 14 premieres lecons respectaient « toute etape requise est questionnee »,
mais rien ne l'imposait — le premier pack qui l'a ignoree a produit une lecon
que l'eleve ne pouvait pas finir.
"""
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from education.models import Chapter, Lesson, Question, Quiz, Step, Subject

U = get_user_model()


def _contenu(nb_mots=70):
    return ' '.join(['alpha'] * nb_mots)


def _contenu_fr(nb_mots=70):
    return ' '.join(['mot'] * nb_mots)


def _qcm(correct='A'):
    return {
        'kind': 'mcq',
        'text': 'Choose one',
        'text_fr': 'Choisis une reponse',
        'explanation': 'Because of the rule',
        'explanation_fr': 'Parce que la regle',
        'choices': [
            {'text': 'A', 'text_fr': 'A', 'correct': correct == 'A'},
            {'text': 'B', 'text_fr': 'B', 'correct': correct == 'B'},
        ],
    }


def pack_valide():
    """Un pack minimal mais reellement conforme : il doit passer tel quel.

    Sert de reference aux tests : on part d'un pack que `check_pack` accepte,
    puis on casse une seule regle a la fois. Sans cela, un test peut passer
    pour la mauvaise raison.
    """
    return {
        'lesson': 18,
        'lesson_fields': {
            'title': 'Titre', 'title_fr': 'Titre',
            'objectives': ['Un objectif'], 'objectives_fr': ['Un objectif'],
        },
        'steps': [{
            'kind': 'concept',
            'title': 'Etape', 'title_fr': 'Etape',
            'content': _contenu(), 'content_fr': _contenu_fr(),
            'required': True,
            'question': _qcm(),
        }],
        'quiz': {
            'title': 'Quiz', 'title_fr': 'Quiz',
            'questions': [_qcm() for _ in range(4)],
        },
    }


class CheckPackTest(TestCase):
    """Le garde-fou doit refuser ce qui casse la lecon, et seulement cela."""

    def _run(self, pack):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'pack.json'
            f.write_text(json.dumps(pack), encoding='utf-8')
            sortie = StringIO()
            try:
                call_command('check_pack', str(f), stdout=sortie, quiet=True)
            except CommandError:
                return sortie.getvalue() + '|REFUSE'
            return sortie.getvalue() + '|OK'

    def test_un_pack_valide_passe(self):
        self.assertTrue(self._run(pack_valide()).endswith('|OK'))

    def test_etape_requise_sans_question_refusee(self):
        #Invariant de jouabilite : l'eleve ne peut jamais « resoudre » une
        # etape sans question, donc l'etape suivante reste verrouillee
        # pour toujours.
        pack = pack_valide()
        del pack['steps'][0]['question']
        sortie = self._run(pack)
        self.assertTrue(sortie.endswith('|REFUSE'))
        self.assertIn('SANS question', sortie)

    def test_etape_facultative_sans_question_acceptee(self):
        # Seules les etapes REQUISES doivent etre questionnees : une etape de
        # lecture facultative n'a pas a l'etre, sinon le lecteur ne progressionne
        # pas. Le refus ci-dessus ne doit donc pas provenir d'autre chose.
        pack = pack_valide()
        pack['steps'].append({
            'kind': 'concept',
            'title': 'Lecture', 'title_fr': 'Lecture',
            'content': _contenu(), 'content_fr': _contenu_fr(),
            'required': False,
        })
        self.assertTrue(self._run(pack).endswith('|OK'))

    def test_etape_trop_courte_refusee(self):
        pack = pack_valide()
        pack['steps'][0]['content'] = 'trois mots'
        self.assertTrue(self._run(pack).endswith('|REFUSE'))

    def test_qcm_a_deux_bonnes_reponses_refuse(self):
        pack = pack_valide()
        pack['quiz']['questions'][0]['choices'][1]['correct'] = True
        self.assertTrue(self._run(pack).endswith('|REFUSE'))

    def test_reponse_numeric_non_convertible_refusee(self):
        # La faute la plus discrete : le correcteur ignore silencieusement une
        # entree non convertible ; si c'est la seule, l'exercice est
        # impossible a reussir.
        pack = pack_valide()
        pack['quiz']['questions'][0] = {
            'kind': 'numeric', 'text': 'q', 'text_fr': 'q',
            'explanation': 'e', 'explanation_fr': 'e',
            'config': {'accepted': ['douze'], 'tolerance': 0},
        }
        self.assertTrue(self._run(pack).endswith('|REFUSE'))

    def test_objectifs_desalignes_refuses(self):
        pack = pack_valide()
        pack['lesson_fields']['objectives_fr'] = ['a', 'b']
        self.assertTrue(self._run(pack).endswith('|REFUSE'))

    def test_francais_contamine_refuse(self):
        # De l'anglais dans un champ francais : c'est ce que le detecteur doit
        # voir. L'inverse (anglais dans le champ anglais) est normal.
        pack = pack_valide()
        pack['quiz']['questions'][0]['text_fr'] = 'the answer is the answer'
        self.assertTrue(self._run(pack).endswith('|REFUSE'))


class TerrainMixin:
    """Fabrique le strict minimum : une matiere, un chapitre, une lecon.

    On construit le terrain dans `setUp` et non `setUpTestData` : place apres
    `TestCase` dans la liste de bases, le mixin se retrouve apres `SimpleTestCase`
    dans la MRO, dont `setUpTestData` l'emporte. En `setUp` il n'y a pas
    d'ambiguite.
    """

    def setUp(self):
        super().setUp()
        self.prof = U.objects.create_user(
            username='prof_t', email='prof_t@test.local', password='x',
            role='teacher')
        self.eleve = U.objects.create_user(
            username='eleve_t', email='eleve_t@test.local', password='x',
            role='student')
        self.matiere = Subject.objects.create(
            name='Test', slug='test', level='secondary')
        self.chapitre = Chapter.objects.create(
            subject=self.matiere, title='C1', title_fr='C1', order=1)
        self.lecon = Lesson.objects.create(
            chapter=self.chapitre, title='L1', title_fr='L1', order=1,
            status='published', objectives=['o'], objectives_fr=['o'])
        self.client = APIClient()

    def _etape(self, **kw):
        d = dict(lesson=self.lecon, order=1, title='E', title_fr='E',
                 content='c', content_fr='c', kind=Step.Kind.CONCEPT)
        d.update(kw)
        return Step.objects.create(**d)

    def _question(self, **kw):
        d = dict(text='t', text_fr='t', explanation='e', explanation_fr='e',
                 kind=Question.Kind.MCQ)
        d.update(kw)
        return Question.objects.create(**d)


class LecteurTest(TerrainMixin, TestCase):
    """Le lecteur doit etre franchissable, et le parcours doit se deverrouiller."""

    def test_progression_du_lecteur(self):
        from education.models import Choice
        q1 = self._question()
        Choice.objects.create(question=q1, text='A', text_fr='A',
                              is_correct=True)
        self._etape(order=1, required=True, question=q1)
        q2 = self._question()
        Choice.objects.create(question=q2, text='A', text_fr='A',
                              is_correct=True)
        self._etape(order=2, required=True, question=q2)

        self.client.force_authenticate(self.eleve)
        etapes = self.client.get(
            f'/api/education/lessons/{self.lecon.pk}/steps/').json()
        self.assertEqual(len(etapes), 2)
        self.assertEqual([s['solved'] for s in etapes], [False, False])

        self.client.post(f'/api/education/exercises/{q1.pk}/attempt/',
                         {'answer': {'choice_id': 1}}, format='json')
        etapes = self.client.get(
            f'/api/education/lessons/{self.lecon.pk}/steps/').json()
        self.assertEqual([s['order'] for s in etapes if s['solved']], [1])


class BrouillonInvisibleTest(TerrainMixin, TestCase):
    """Un brouillon n'existe pas pour un eleve, meme par id devine.

    Observe sur la lecon 18 : `dev_eleve` a obtenu `correct_choice_id` et
    l'explication d'une question de lecon en `draft` en devinant l'identifiant.
    """

    def setUp(self):
        super().setUp()
        from education.models import Choice
        self.q = self._question()
        self.bonne = Choice.objects.create(
            question=self.q, text='A', text_fr='A', is_correct=True)
        Choice.objects.create(question=self.q, text='B', text_fr='B')
        self._etape(required=True, question=self.q)
        self.quiz = Quiz.objects.create(
            lesson=self.lecon, title='Q', title_fr='Q', pass_score=60)
        self.quiz.questions.create(
            text='q', text_fr='q', explanation='e', explanation_fr='e',
            kind=Question.Kind.MCQ, order=1)
        self.lecon.status = 'draft'
        self.lecon.save()
        self.client.force_authenticate(self.eleve)

    def test_reponse_interdite(self):
        r = self.client.post(
            f'/api/education/exercises/{self.q.pk}/attempt/',
            {'answer': {'choice_id': self.bonne.pk}}, format='json')
        self.assertEqual(r.status_code, 404)
        self.assertNotIn('correct_choice_id', r.json())

    def test_indice_interdit(self):
        r = self.client.get(
            f'/api/education/exercises/{self.q.pk}/reveal_hint/')
        self.assertEqual(r.status_code, 404)

    def test_quiz_interdit(self):
        r = self.client.get(f'/api/education/quizzes/{self.quiz.pk}/')
        self.assertEqual(r.status_code, 404)

    def test_absent_du_catalogue(self):
        r = self.client.get('/api/education/lessons/')
        self.assertNotIn(self.lecon.pk, [x['id'] for x in r.json()])

    def test_aucune_tentative_enregistree(self):
        self.client.post(f'/api/education/exercises/{self.q.pk}/attempt/',
                         {'answer': {'choice_id': self.bonne.pk}}, 'json')
        from education.models import ExerciseAttempt
        self.assertEqual(ExerciseAttempt.objects.filter(
            student=self.eleve).count(), 0)

    def test_l_enseignant_peut_tester_avant_publication(self):
        # Sans cela, on ne pourrait pas verifier le cheminement avant de
        # publier — donc on publierait sans l'avoir jamais vu fonctionner.
        self.client.force_authenticate(self.prof)
        r = self.client.post(
            f'/api/education/exercises/{self.q.pk}/attempt/',
            {'answer': {'choice_id': self.bonne.pk}}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_la_lecon_publiee_reste_atteignable(self):
        self.lecon.status = 'published'
        self.lecon.save()
        r = self.client.post(
            f'/api/education/exercises/{self.q.pk}/attempt/',
            {'answer': {'choice_id': self.bonne.pk}}, format='json')
        self.assertEqual(r.status_code, 200)


class LeconPubliqueTest(TerrainMixin, TestCase):
    """§4 et §10 : le visiteur consulte les ressources « selectionnees ».

    Le cahier des charges dit que le visiteur « views public information and
    selected educational resources ». Avant ce travail, un visiteur pouvait
    lister les 14 lecons publiees et n'en ouvrir aucune : la porte etait
    fermee au contenu tout en laissant voir la vitrine.

    Ces tests verrouillent la porte dans les deux sens, parce que les deux
    moities sont facile a casser :

    - une lecon cochee publique s'ouvre SANS compte ;
    - une lecon non cochee reste fermee au visiteur, meme si elle est publiee ;
    - un brouillon ne s'ouvre jamais, coche ou non ;
    - un membre connecte lit les lecons publiees comme avant.
    """

    def setUp(self):
        super().setUp()
        self._etape()
        self.lecon.is_public = True
        self.lecon.save()

    def _visiteur(self):
        return APIClient()

    def test_la_lecon_publique_s_ouvre_sans_compte(self):
        r = self._visiteur().get(f'/api/education/lessons/{self.lecon.pk}/')
        self.assertEqual(r.status_code, 200)

    def test_les_etapes_de_la_lecon_publique_sont_lisibles(self):
        r = self._visiteur().get(f'/api/education/lessons/{self.lecon.pk}/steps/')
        self.assertEqual(r.status_code, 200)

    def test_lecon_publiee_mais_non_cochee_reste_fermee(self):
        # C'est le point de la decision : « publiee » ne veut pas dire
        # « ouverte ». Ouvrir tout par defaut exposerait la pedagogie sans
        # que l'association l'ait choisi.
        self.lecon.is_public = False
        self.lecon.save()
        r = self._visiteur().get(f'/api/education/lessons/{self.lecon.pk}/')
        self.assertEqual(r.status_code, 404)

    def test_un_brouillon_ne_s_ouvre_jamais_meme_coche(self):
        self.lecon.status = 'draft'
        self.lecon.is_public = True
        self.lecon.save()
        r = self._visiteur().get(f'/api/education/lessons/{self.lecon.pk}/')
        self.assertEqual(r.status_code, 404)

    def test_le_visiteur_ne_peut_pas_ecrire_sa_progression(self):
        # `progress` cree un LessonMastery lie a l'utilisateur : un visiteur
        # sans compte y provoquerait une erreur 500.
        r = self._visiteur().get(
            f'/api/education/lessons/{self.lecon.pk}/progress/')
        self.assertEqual(r.status_code, 401)

    def test_le_membre_connecte_lit_une_lecon_publiee_non_cochee(self):
        self.lecon.is_public = False
        self.lecon.save()
        self.client.force_authenticate(self.eleve)
        r = self.client.get(f'/api/education/lessons/{self.lecon.pk}/')
        self.assertEqual(r.status_code, 200)

    def test_le_catalogue_annonce_la_visibilite(self):
        # Le frontend doit pouvoir afficher « accessible sans compte » sans
        # deviner : le drapeau voyage dans la reponse.
        r = self._visiteur().get('/api/education/lessons/')
        ids = [x['id'] for x in r.json()]
        fiche = next(x for x in r.json() if x['id'] == self.lecon.pk)
        self.assertIn(self.lecon.pk, ids)
        self.assertTrue(fiche['is_public'])