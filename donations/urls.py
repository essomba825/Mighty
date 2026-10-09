from rest_framework.routers import DefaultRouter

from .views import ContributionViewSet, PartnershipRequestViewSet

router = DefaultRouter()
router.register('contributions', ContributionViewSet, basename='contribution')
router.register('partnerships', PartnershipRequestViewSet, basename='partnership')

urlpatterns = router.urls
