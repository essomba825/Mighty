from rest_framework.routers import DefaultRouter

from .views import ExamPaperViewSet, ExamSubmissionViewSet

router = DefaultRouter()
router.register('papers', ExamPaperViewSet, basename='exam-paper')
router.register('submissions', ExamSubmissionViewSet, basename='exam-submission')

urlpatterns = router.urls
