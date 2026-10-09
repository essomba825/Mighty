import json
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import ActivityLog
from accounts.management.commands import backup_data as backup_mod
from education.models import Chapter, Lesson, Subject

User = get_user_model()


class JournalTest(TestCase):
    """§9 : le journal doit existir, et ne doit jamais casser la requete."""

    def test_une_connexion_reussie_est_tracee(self):
        user = User.objects.create_user(username='j1', email='j1@test.local',
                                        password='MotDePasse123!')
        r = APIClient().post('/api/auth/login/',
                             {'identifier': 'j1@test.local',
                              'password': 'MotDePasse123!'}, format='json')
        self.assertEqual(r.status_code, 200)
        entree = ActivityLog.objects.filter(action='login').first()
        self.assertIsNotNone(entree)
        self.assertEqual(entree.actor_id, user.pk)

    def test_une_connexion_ratee_nest_pas_tracee(self):
        # Le journal ne doit pas devenir un moyen de tester des comptes.
        User.objects.create_user(username='j2', email='j2@test.local',
                                 password='MotDePasse123!')
        APIClient().post('/api/auth/login/',
                         {'identifier': 'j2@test.local', 'password': 'faux'},
                         format='json')
        self.assertEqual(ActivityLog.objects.filter(action='login').count(), 0)

    def test_le_nom_est_copie_pour_survenir_a_la_suppression_du_compte(self):
        from accounts.journal import record
        user = User.objects.create_user(username='j3', email='j3@test.local',
                                        password='x')
        record(actor=user, action='update', model_name='Lesson',
               object_id=1, summary='test')
        avant = ActivityLog.objects.get()
        user.delete()
        self.assertEqual(ActivityLog.objects.count(), 1)
        ligne = ActivityLog.objects.first()
        self.assertIsNone(ligne.actor)
        # Le libelle survit a la suppression du compte : c'est tout l'interet.
        self.assertEqual(ligne.actor_label, avant.actor_label)
        self.assertTrue(ligne.actor_label)

    def test_un_journal_indisponible_ne_renvoie_pas_erreur(self):
        # Le scenario redouté : la base pleine, le journal plante, et la
        # connexion de l'eleve tombe avec. Le journal s'efface, l'action passe.
        from accounts import journal
        original = ActivityLog.objects.create

        def casse(*args, **kwargs):
            raise Exception('disque plein')

        ActivityLog.objects.create = casse
        try:
            self.assertIsNone(journal.record(actor=None, action='create',
                                             summary='x'))
        finally:
            ActivityLog.objects.create = original


class SauvegardeTest(TestCase):
    """§6 : la sauvegarde doit etre reellement restaurable."""

    def setUp(self):
        self.avant = set(ActivityLog.objects.values_list('id', flat=True))

    def test_la_copie_contient_les_donnees(self):
        User.objects.create_user(username='b1', email='b1@test.local',
                                 password='x')
        dest = tempfile.mkdtemp()
        try:
            from django.core.management import call_command
            call_command('backup_data', dest=dest, keep=0,
                         sans_medias=True, verbosity=0)
            dossiers = [d for d in os.listdir(dest)
                        if os.path.isdir(os.path.join(dest, d))]
            self.assertEqual(len(dossiers), 1)
            copie = os.path.join(dest, dossiers[0], 'db.sqlite3')
            self.assertTrue(os.path.exists(copie))

            import sqlite3
            with sqlite3.connect(copie) as c:
                self.assertEqual(
                    c.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                n = c.execute('SELECT COUNT(*) FROM accounts_user').fetchone()[0]
            self.assertGreaterEqual(n, 1)

            manifeste = os.path.join(dest, dossiers[0], 'manifest.json')
            donnees = json.load(open(manifeste, encoding='utf-8'))
            self.assertIn('tables', donnees)
            self.assertGreater(donnees['total_rows'], 0)
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    def test_la_sauvegarde_est_elle_meme_tracee(self):
        dest = tempfile.mkdtemp()
        try:
            from django.core.management import call_command
            avant = ActivityLog.objects.count()
            call_command('backup_data', dest=dest, keep=0,
                         sans_medias=True, verbosity=0)
            self.assertGreater(ActivityLog.objects.count(), avant)
            self.assertTrue(ActivityLog.objects.filter(action='backup').exists())
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    def test_la_retention_ne_garde_que_n_sauvegardes(self):
        dest = tempfile.mkdtemp()
        try:
            from django.core.management import call_command
            # Deux sauvegardes ne doivent pas se marcher dessus quand elles
            # tombent dans la meme seconde : le dossier est suffixe, sinon la
            # commande echoue sur un `mkdir` deja existant — et une sauvegarde
            # qui echoue en silence fait croire qu'on est couvert.
            for _ in range(3):
                call_command('backup_data', dest=dest, keep=2,
                             sans_medias=True, verbosity=0)
            dossiers = [d for d in os.listdir(dest)
                        if os.path.isdir(os.path.join(dest, d))]
            self.assertEqual(len(dossiers), 2)
        finally:
            shutil.rmtree(dest, ignore_errors=True)


class PublicationJournaliseeTest(TestCase):
    """Publier et rejeter une lecon doit laisser une trace (§9)."""

    def setUp(self):
        self.prof = User.objects.create_user(
            username='pj', email='pj@test.local', password='x',
            role='teacher', is_staff=True)
        s = Subject.objects.create(name='J', slug='journal-test', level='secondary')
        c = Chapter.objects.create(subject=s, title='C', title_fr='C', order=1)
        self.lecon = Lesson.objects.create(
            chapter=c, title='L', title_fr='L', order=1, status='pending',
            objectives=['o'], objectives_fr=['o'])
        self.client = APIClient()
        self.client.force_authenticate(self.prof)

    def test_le_rejet_est_tracee(self):
        # On passe par le rejet, dont le chemin est court : la lecon doit etre
        # en attente. Le but est le journal, pas le controle qualite.
        r = self.client.post(f'/api/education/lessons/{self.lecon.pk}/reject/')
        self.assertEqual(r.status_code, 200)
        self.lecon.refresh_from_db()
        self.assertEqual(self.lecon.status, 'draft')
        entree = ActivityLog.objects.filter(action='reject').first()
        self.assertIsNotNone(entree)
        self.assertEqual(entree.object_id, str(self.lecon.pk))

    def test_une_publication_refusee_par_la_qualite_nest_pas_tracee(self):
        # Le journal ne doit pas annoncer une publication qui n'a pas eu lieu :
        # une lecon sans etapes questionnees echoue au controle qualite, et la
        # ligne doit rester absente.
        r = self.client.post(f'/api/education/lessons/{self.lecon.pk}/validate/')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(ActivityLog.objects.filter(action='publish').exists())

    def test_la_publication_reussie_est_tracee(self):
        from education.models import Question, Step
        q = Question.objects.create(text='q', text_fr='q', kind='mcq')
        Step.objects.create(lesson=self.lecon, order=1, title='E', title_fr='E',
                           content='c' * 80, content_fr='c' * 80,
                           required=False)
        r = self.client.post(f'/api/education/lessons/{self.lecon.pk}/validate/')
        self.assertEqual(r.status_code, 200, r.content[:300])
        entree = ActivityLog.objects.filter(action='publish').first()
        self.assertIsNotNone(entree)
        self.assertEqual(entree.object_id, str(self.lecon.pk))