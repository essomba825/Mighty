from rest_framework.routers import DefaultRouter

from .views import PaymentRequestViewSet, PaymentViewSet

router = DefaultRouter()
# « requests » d'abord : sans cela « payments/requests/… » tomberait dans le
# détail de PaymentViewSet (pk = "requests") et renverrait 404/405.
router.register('requests', PaymentRequestViewSet, basename='payment-request')
router.register('', PaymentViewSet, basename='payment')

urlpatterns = router.urls