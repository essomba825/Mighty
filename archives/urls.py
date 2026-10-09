from rest_framework.routers import DefaultRouter

from .views import ArchiveDocumentViewSet

router = DefaultRouter()
router.register('', ArchiveDocumentViewSet, basename='archive')

urlpatterns = router.urls
