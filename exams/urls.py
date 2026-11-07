from rest_framework.routers import DefaultRouter

from .views import ExamPaperViewSet

router = DefaultRouter()
router.register('papers', ExamPaperViewSet, basename='exam-paper')

urlpatterns = router.urls
