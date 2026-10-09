from rest_framework.routers import DefaultRouter

from .views import NewsArticleViewSet

router = DefaultRouter()
router.register('', NewsArticleViewSet, basename='news')

urlpatterns = router.urls
