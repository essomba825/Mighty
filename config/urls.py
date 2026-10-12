import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from .stats_views import PublicHighlightsView, StatsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/alumni/', include('alumni.urls')),
    path('api/events/', include('events.urls')),
    path('api/news/', include('news.urls')),
    path('api/archives/', include('archives.urls')),
    path('api/projects/', include('projects.urls')),
    path('api/donations/', include('donations.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/education/', include('education.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/mentorship/', include('mentorship.urls')),
    path('api/contact/', include('contact.urls')),
    path('api/stats/', StatsView.as_view(), name='stats'),
    path('api/highlights/', PublicHighlightsView.as_view(), name='highlights'),
]

# Les medias sont versionnes dans le depot (backend/media) et doivent rester
# servis en production. Attention : `django.conf.urls.static.static()` ne
# renvoie ses routes que si DEBUG=True — en production /media/ n'existait donc
# pas et toutes les images du site (projets, actualites, evenements, archives,
# galerie, photos de profil) renvoyaient une 404. On declare la route
# explicitement, quel que soit DEBUG.
urlpatterns += [
    re_path(
        r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')),
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
