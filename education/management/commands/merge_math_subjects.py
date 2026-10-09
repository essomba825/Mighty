"""Reunit les deux matieres de maths OL dans un seul catalogue.

Contexte : `mathematiques-ol` (id 1) et `mathematics-ol` (id 5) sont la meme
matiere sous deux slugs. `mathematiques-ol` ne porte que des chapitres de
substitution nommes « Chapter 1/2/3 », mais contient trois lecones redigees et
validees que la seconde n'a pas. On garde `mathematics-ol` comme slug canonique
 parce que c'est la que se trouve le programme complet en huit chapitres, et on
deplace les trois lecones vers lui.

Usage :
    python manage.py merge_math_subjects --dry-run
    python manage.py merge_math_subjects --apply
    python manage.py merge_math_subjects --apply --purge-legacy

L'idempotence est stricte : relancer la commande apres un succes ne fait rien
de plus. `--purge-legacy` est separe pour ne jamais supprimer une matiere par
habitude.

Aucune lecon publiee n'est modifiee : on ne touche qu'a son chapitre et a son
ordre, jamais a son contenu.
"""
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from education.models import Chapter, Lesson, Subject

CANONIQUE = 'mathematics-ol'
LEGACY = 'mathematiques-ol'

# Lecon legacy -> (chapitre cible dans le canonique, ordre cible, placement)
# On place la lecon 3 AVANT la 16 : elle definit le nombre rationnel, la forme
# irreductible et le signe du denominateur, ce que la 16 suppose deja acquis.
MIGRATIONS = [
    {
        'lecon': 8,
        'chapitre': 3,
        'ordre': 2,
        'remplace': 23,          # squelette vide a liberer
        'raison': 'Solving Linear Equations of the First Degree -> chapitre 3',
    },
    {
        'lecon': 11,
        'chapitre': None,        # chapitre a creer
        'chapitre_titre': 'Exam Practice',
        'ordre': 1,
        'raison': 'Sujet GCE 2024 + corrige -> chapitre dedie',
    },
    {
        'lecon': 3,
        'chapitre': 1,
        'ordre': 2,
        'decale': [16, 17, 18],  # a pousser d'un rang vers la fin
        'raison': 'Fractions and Rational Numbers -> socle du chapitre 1',
    },
]


class Command(BaseCommand):
    help = "Reunit mathematiques-ol et mathematics-ol dans un catalogue unique"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Ecrit les deplacements (sinon apercu)')
        parser.add_argument('--purge-legacy', action='store_true',
                            help='Supprime la matiere legacy vide apres migration')
        parser.add_argument('--no-backup', action='store_true',
                            help='Ne pas faire de copie du fichier SQLite')

    def handle(self, *args, **options):
        canonique = Subject.objects.filter(slug=CANONIQUE).first()
        legacy = Subject.objects.filter(slug=LEGACY).first()
        if canonique is None:
            raise CommandError(f'Slug canonique absent : {CANONIQUE}')
        if legacy is None:
            self.stdout.write(self.style.WARNING(
                f'{LEGACY} a deja disparu. Rien a faire.'))
            return

        self.stdout.write(f'canonique : {canonique.slug} (id {canonique.id}, '
                          f'{canonique.chapters.count()} chapitres)')
        self.stdout.write(f'legacy    : {legacy.slug} (id {legacy.id}, '
                          f'{legacy.chapters.count()} chapitres, '
                          f'{Lesson.objects.filter(chapter__subject=legacy).count()} lecons)')
        self.stdout.write('')

        restants = [m for m in MIGRATIONS
                    if Lesson.objects.filter(pk=m['lecon']).exists()
                    and Lesson.objects.get(pk=m['lecon']).chapter.subject_id
                    != canonique.id]
        deja_faits = [m for m in MIGRATIONS if m not in restants]

        for m in deja_faits:
            l = Lesson.objects.get(pk=m['lecon'])
            self.stdout.write(self.style.SUCCESS(
                f'  deja fait : lecon {l.id} est dans {l.chapter.subject.slug}'))

        if not restants:
            self.stdout.write(self.style.SUCCESS('RIEN A DEPLACER.'))
            return self._purge(legacy, options)

        for m in restants:
            self.stdout.write(f'  a deplacer : {m["raison"]}')

        self._controles(legacy, canonique)

        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                '\nAPERCU. Relance avec --apply pour ecrire.'))
            return

        if not options['no_backup']:
            self._sauvegarde()

        with transaction.atomic():
            for m in restants:
                self._deplacer(m, canonique)

        self.stdout.write('')
        self._rapport(canonique, legacy)
        self._purge(legacy, options)

    # ------------------------------------------------------------------
    def _controles(self, legacy, canonique):
        """Refuse de migrer si une des lecones de depart contient encore
        autre chose que le contenu attendu, ou si la cible est occupee."""
        for m in MIGRATIONS:
            l = Lesson.objects.filter(pk=m['lecon']).first()
            if l is None:
                continue
            if l.chapter.subject_id == canonique.id:
                continue
            etapes = l.steps.count()
            if etapes == 0:
                raise CommandError(
                    f'Lecon {l.id} (« {l.title} ») est vide alors qu\'elle '
                    f'devrait contenir le contenu migre. Arret.')
            if l.status == 'published':
                self.stdout.write(self.style.WARNING(
                    f'  attention : lecon {l.id} est publiee, seul son '
                    f'chapitre sera deplace'))

        # La cible de la lecon 8 doit etre libre.
        squelette = Lesson.objects.filter(pk=23).first()
        if squelette is not None and squelette.chapter.subject_id != canonique.id:
            if squelette.steps.count():
                raise CommandError(
                    f'Le squelette 23 contient {squelette.steps.count()} '
                    f'etape(s). Il ne sera pas ecrase. Arret.')

    def _sauvegarde(self):
        from django.conf import settings
        base = Path(settings.DATABASES['default']['NAME'])
        if not base.exists():
            self.stdout.write('  (pas de fichier SQLite a copier)')
            return
        destination = base.with_name(f'{base.stem}-backup-merge.sqlite3')
        shutil.copy2(base, destination)
        self.stdout.write(self.style.SUCCESS(
            f'  sauvegarde : {destination.name}'))

    def _deplacer(self, m, canonique):
        l = Lesson.objects.get(pk=m['lecon'])

        if m.get('remplace'):
            a_supprimer = Lesson.objects.filter(pk=m['remplace']).first()
            if a_supprimer is not None:
                if a_supprimer.steps.count():
                    raise CommandError(
                        f'Lecon {a_supprimer.id} n\'est plus vide, abandon')
                a_supprimer.delete()
                self.stdout.write(f'  squelette {m["remplace"]} supprime')

        chapitre = self._chapitre(m, canonique)

        if m.get('decale'):
            self._decaler(chapitre, m['decale'], avant=m['ordre'])

        l.chapter = chapitre
        l.order = m['ordre']
        l.save(update_fields=['chapter', 'order'])
        self.stdout.write(self.style.SUCCESS(
            f'  lecon {l.id} « {l.title} » -> {canonique.slug} '
            f'ch{chapitre.order} lo{l.order}'))

    def _chapitre(self, m, canonique):
        if m.get('chapitre') is None:
            titre = m['chapitre_titre']
            chapitre = canonique.chapters.filter(title=titre).first()
            if chapitre is None:
                dernier = canonique.chapters.aggregate(
                    m=Max('order'))['m'] or 0
                chapitre = Chapter.objects.create(
                    subject=canonique, order=dernier + 1, title=titre,
                    title_fr=titre)
                self.stdout.write(f'  chapitre cree : « {titre} » '
                                  f'(ordre {chapitre.order})')
            return chapitre

        chapitre = canonique.chapters.filter(order=m['chapitre']).first()
        if chapitre is None:
            raise CommandError(
                f'Chapitre {m["chapitre"]} absent de {canonique.slug}')
        return chapitre

    def _decaler(self, chapitre, ids, avant):
        """Pousse les lecons `ids` d'un rang vers la fin, de la plus haute a la
        plus basse, pour ne jamais ecraser un ordre deja occupe.

        On itere du plus grand numero d'ordre vers le plus petit : decaler le
        plus grand d'abord libere la place du suivant.
        """
        for lid in sorted(
                ids, key=lambda i: -(Lesson.objects.get(pk=i).order
                                     if Lesson.objects.filter(pk=i).exists()
                                     else 0)):
            l = Lesson.objects.get(pk=lid)
            if l.chapter_id != chapitre.id:
                continue
            l.order = max(l.order, avant) + 1
            l.save(update_fields=['order'])
            self.stdout.write(f'    lecon {l.id} decalee -> lo{l.order}')

    def _rapport(self, canonique, legacy):
        self.stdout.write('')
        restants = Lesson.objects.filter(chapter__subject=legacy)
        self.stdout.write(f'  reste dans {legacy.slug} : {restants.count()} lecon(s)'
                          f' | {legacy.chapters.count()} chapitre(s)')
        for ch in canonique.chapters.order_by('order'):
            lecons = ch.lessons.count()
            vides = ch.lessons.filter(steps__isnull=True).count()
            self.stdout.write(f'    ch{ch.order} {ch.title} : {lecons} lecon(s)'
                              + (f', {vides} vide(s)' if vides else ''))

    def _purge(self, legacy, options):
        lecons = Lesson.objects.filter(chapter__subject=legacy).count()
        if lecons:
            self.stdout.write(self.style.WARNING(
                f'\n{legacy.slug} contient encore {lecons} lecon(s) : '
                f'non supprimee.'))
            return
        if not options['purge_legacy']:
            self.stdout.write(self.style.WARNING(
                f'\n{legacy.slug} est vide. Relance avec --purge-legacy '
                f'pour la supprimer.'))
            return
        if not options['apply']:
            self.stdout.write(self.style.WARNING('APERCU : --purge-legacy '
                                                'demande aussi --apply.'))
            return
        nb = legacy.chapters.count()
        legacy.delete()
        self.stdout.write(self.style.SUCCESS(
            f'\n{legacy.slug} supprimee ({nb} chapitres, 0 lecon).'))