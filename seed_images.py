"""Attache des images aux actualités, événements et projets."""
import django, os, random, urllib.request
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.files.base import ContentFile
from news.models import NewsArticle
from events.models import Event
from projects.models import Project

random.seed(42)


def fetch_image(seed, w=900, h=550):
    """Image d'illustration libre (picsum.photos)."""
    url = f'https://picsum.photos/seed/{seed}/{w}/{h}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def attach(model, field='image'):
    qs = model.objects.all()
    ok = 0
    for obj in qs:
        if getattr(obj, field):
            continue
        try:
            seed = f'mms-{model.__name__.lower()}-{obj.id}'
            data = fetch_image(seed)
            getattr(obj, field).save(f'{seed}.jpg', ContentFile(data), save=True)
            ok += 1
        except Exception as e:
            print(f'  skip {obj.pk}: {e}')
    print(f'{model.__name__}: {ok} images ajoutées')


attach(NewsArticle)
attach(Event)
attach(Project)
print('Terminé.')
