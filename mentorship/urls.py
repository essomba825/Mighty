from rest_framework.routers import DefaultRouter

from .views import MentorshipOfferViewSet, MentorshipRequestViewSet

router = DefaultRouter()
router.register('offers', MentorshipOfferViewSet, basename='mentorship-offer')
router.register('requests', MentorshipRequestViewSet, basename='mentorship-request')

urlpatterns = router.urls
