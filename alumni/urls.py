from rest_framework.routers import DefaultRouter

from .views import AlumniProfileViewSet

router = DefaultRouter()
router.register('profiles', AlumniProfileViewSet, basename='alumni-profile')

urlpatterns = router.urls
