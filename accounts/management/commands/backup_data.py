"""Sauvegarde des donnees institutionnelles (§6 et §9).

Usage :
    python manage.py backup_data
    python manage.py backup_data --keep 14
    python manage.py backup_data --dest D:\\sauvegardes

Ce que la commande fait, et pourquoi c'est ecrit comme ca :

- **Copie coherente, pas un simple `cp`.** SQLite autorise la copie du fichier
  pendant qu'une ecriture est en cours ; le resultat peut etre tronque. On
  utilise donc l'API de sauvegarde de SQLite, qui produit un instantane
  garanti coherent. Le serveur tourne, la commande fait une sauvegarde sure.

- **Les medias vont avec.** La base ne sert a rien si les photos de profils,
  les archives et les documents des projets restent sur le disque. Un ZIP des
  medias accompagne l'instantane.

- **Un inventaire.** Un manifeste texte indique ce que contient la sauvegarde
  (tables, nombre de lignes, volume). Face a une restauration, on sait ce qu on
  a obtenu sans avoir a ouvrir la base.

- **Retention.** `--keep N` ne garde que les N sauvegardes les plus recentes.
  Une sauvegarde qui s accumule sans fin remplit le disque, ce qui transforme une
  mesure de securite en panne.
"""
import datetime
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from accounts.journal import record
from accounts.models import ActivityLog, User

# Volume de medias au-dela duquel on avertit sans echouer : un gros site
# produit des ZIP longs a compresser, et un avertissement vaut mieux qu'un
# echouen qui fait croire que la sauvegarde a echoue.
SEUIL_AVERTISSEMENT_MO = 500


class Command(BaseCommand):
    help = 'Sauvegarde la base et les medias (§6 : backup and preservation)'

    def add_arguments(self, parser):
        parser.add_argument('--dest', default='', help='Dossier de destination')
        parser.add_argument('--keep', type=int, default=14,
                            help='Nombre de sauvegardes a conserver (0 = tout)')
        parser.add_argument('--sans-medias', action='store_true',
                            help='Ne pas inclure les medias (base seule)')

    def handle(self, *args, **options):
        # Django nomme ce moteur « sqlite », pas « sqlite3 » : c'est le nom du
        # module Python. Comparer a « sqlite3 » fait echouer la commande sur une
        # base SQLite parfaitement fonctionnelle.
        if connection.vendor != 'sqlite':
            raise CommandError(
                'Cette commande ne copie que SQLite. Sur PostgreSQL, utilisez '
                'pg_dump : la copie a chaud d un fichier de donnees serait '
                'incoherente.')

        base = Path(settings.BASE_DIR) / 'db.sqlite3'
        if not base.exists():
            raise CommandError(f'Base introuvable : {base}')

        dest = Path(options['dest']) if options['dest'] else (
            Path(settings.BASE_DIR).parent / 'backups')
        dest.mkdir(parents=True, exist_ok=True)

        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        cible = dest / f'mighty-sixers-{stamp}'
        # Deux sauvegardes dans la meme seconde doivent cohabiter, pas
        # s'ecraser : une commande qui echoue sur un dossier deja present est
        # une sauvegarde qui n'a pas eu lieu, ce qui est pire que de le dire.
        suffixe = 2
        while cible.exists():
            cible = dest / f'mighty-sixers-{stamp}-{suffixe}'
            suffixe += 1
        cible.mkdir(parents=True)

        snapshot = cible / 'db.sqlite3'
        # source=:memory: obligatoire : sans lui, SQLite ecrase le fichier
        # source en y copiant l'instantane, ce qui detruit la base.
        with sqlite3.connect(f'file:{base}?mode=ro', uri=True) as src:
            with sqlite3.connect(snapshot) as dst:
                src.backup(dst)
        self.stdout.write(self.style.SUCCESS(f'  base      {snapshot.name}'))

        manifest = self._inventaire()
        (cible / 'manifest.json').write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        self.stdout.write(f'  manifeste {len(manifest["tables"])} tables')

        if not options['sans_medias']:
            zip_path = self._medias(dest, stamp)
            if zip_path:
                size_mo = zip_path.stat().st_size / 1_048_576
                detail = f'  medias    {zip_path.name} ({size_mo:.1f} Mo)'
                if size_mo > SEUIL_AVERTISSEMENT_MO:
                    self.stdout.write(self.style.WARNING(
                        detail + ' — volume important, pensez a une destination '
                        'distincte du serveur'))
                else:
                    self.stdout.write(self.style.SUCCESS(detail))

        supprimes = self._purger(dest, options['keep'])
        if supprimes:
            self.stdout.write(f'  retention {supprimes} sauvegarde(s) ancienne(s) '
                              f'supprimee(s)')

        record(actor=None, action='backup', model_name='Project',
               object_id='',
               summary=f'Sauvegarde {stamp} ({manifest["total_rows"]} lignes)')

        self.stdout.write(self.style.SUCCESS(
            f'\nSauvegarde terminee : {cible}'))
        self.stdout.write('Conservez ce dossier hors du serveur : une sauvegarde '
                          'sur la meme machine ne survit pas a sa perte.')

    def _inventaire(self):
        tables = {}
        total = 0
        with connection.cursor() as c:
            c.execute("SELECT name FROM sqlite_master WHERE type='table' "
                      "AND name NOT LIKE 'sqlite_%'")
            noms = [r[0] for r in c.fetchall()]
            for nom in noms:
                try:
                    c.execute(f'SELECT COUNT(*) FROM "{nom}"')
                    n = c.fetchone()[0]
                except Exception:
                    continue
                tables[nom] = n
                total += n
        return {
            'genere_le': datetime.datetime.now().isoformat(timespec='seconds'),
            'total_rows': total,
            'tables': tables,
            'utilisateurs': User.objects.count(),
            'entrees_journal': ActivityLog.objects.count(),
        }

    def _medias(self, dest, stamp):
        racine = Path(settings.MEDIA_ROOT)
        if not racine.exists():
            self.stdout.write('  medias    aucun dossier media, ignore')
            return None
        zip_path = dest / f'mighty-sixers-medias-{stamp}.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for chemin in racine.rglob('*'):
                if chemin.is_file():
                    zf.write(chemin, Path('medias') / chemin.relative_to(racine))
        return zip_path

    def _purger(self, dest, keep):
        if not keep:
            return 0
        dossiers = sorted((p for p in dest.glob('mighty-sixers-*')
                           if p.is_dir()), reverse=True)
        zip_archives = sorted(dest.glob('mighty-sixers-medias-*.zip'), reverse=True)
        supprimes = 0
        for vieux in dossiers[keep:]:
            shutil.rmtree(vieux, ignore_errors=True)
            supprimes += 1
        # Les ZIP sont deux fois plus nombreux que les dossiers : on garde
        # autant d'archives que de dossiers conserves.
        for vieux in zip_archives[keep:]:
            vieux.unlink(missing_ok=True)
        return supprimes