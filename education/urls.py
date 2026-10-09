from rest_framework.routers import DefaultRouter

from .views import (ExerciseViewSet, LessonViewSet, QuizAttemptViewSet, QuizViewSet,
                   SubjectViewSet)

router = DefaultRouter()
router.register('subjects', SubjectViewSet, basename='subject')
router.register('lessons', LessonViewSet, basename='lesson')
router.register('exercises', ExerciseViewSet, basename='exercise')
router.register('quizzes', QuizViewSet, basename='quiz')
router.register('results', QuizAttemptViewSet, basename='quiz-result')

urlpatterns = router.urls
