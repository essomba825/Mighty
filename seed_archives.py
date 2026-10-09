"""Archives de test : photos et documents historiques."""
import django, os, urllib.request

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.files.base import ContentFile
from archives.models import ArchiveDocument

if ArchiveDocument.objects.exists():
    print('Archives déjà présentes, rien à faire.')
else:
    docs = [
        ("Photo de classe — Promotion 1998", "La mythique promotion 1998 devant le bâtiment principal.", 'photo', 1998),
        ("Remise des prix 2003", "Cérémonie annuelle de remise des prix d'excellence.", 'photo', 2003),
        ("Tournoi inter-classes 2005", "Finale du tournoi de basket, victoire de la Terminale C.", 'photo', 2005),
        ("Le premier ordinateur du labo (2001)", "L'arrivée du premier PC, un événement à l'époque !", 'photo', 2001),
        ("Sortie pédagogique au Mont Nlonako", "Les élèves de 4e en excursion géologie.", 'photo', 2008),
        ("Fanfare de l'école — Fête de la jeunesse", "Notre fanfare primée au niveau régional.", 'photo', 2010),
        ("Défilé du 20 mai — années 90", "Nos aînés lors des défilés patriotiques.", 'photo', 1995),
        ("Campagne de reboisement 2012", "200 arbres plantés par les élèves et les anciens.", 'photo', 2012),
        ("Bulletin officiel — Palmarès 1987", "Extrait du palmarès historique de l'école.", 'pdf', 1987),
        ("Règlement intérieur (édition 1990)", "Document fondateur, collection archives.", 'pdf', 1990),
    ]

    for i, (title, desc, dtype, year) in enumerate(docs):
        try:
            if dtype == 'photo':
                url = f'https://picsum.photos/seed/mms-archive-{i}/800/600'
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                data = urllib.request.urlopen(req, timeout=30).read()
                doc = ArchiveDocument(title=title, description=desc, doc_type=dtype,
                                      year=year, is_public=True)
                doc.file.save(f'mms-archive-{i}.jpg', ContentFile(data), save=True)
            else:
                # PDF minimal valide
                pdf = (b'%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n'
                       b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n'
                       b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >> endobj\n'
                       b'xref\n0 4\n0000000000 65535 f \ntrailer << /Size 4 /Root 1 0 R >>\n%%EOF')
                doc = ArchiveDocument(title=title, description=desc, doc_type=dtype,
                                      year=year, is_public=True)
                doc.file.save(f'mms-archive-{i}.pdf', ContentFile(pdf), save=True)
        except Exception as e:
            print(f'  skip {title}: {e}')
    print(f'Archives créées : {ArchiveDocument.objects.count()}')
