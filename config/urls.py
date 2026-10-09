from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
