"""Statistiques globales de la plateforme (réservé aux admins)."""
from django.contrib.auth import get_user_model
from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()

# Année de départ de l'association (bloc "Our story" de l'accueil).
FOUNDING_YEAR = 2009


class PublicHighlightsView(APIView):
    """Chiffres clés publics pour la page d'accueil."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from alumni.models import AlumniProfile
        from donations.models import Contribution
        from education.models import ExerciseAttempt, Lesson, LessonProgress, QuizAttempt
        from projects.models import Project

        # Élèves "touchés" : tout compte ayant déjà appris sur la plateforme
        # (progression, exercice ou quiz) + les comptes de type élève.
        learner_ids = set(LessonProgress.objects.values_list('student', flat=True))
        learner_ids |= set(ExerciseAttempt.objects.values_list('student', flat=True))
        learner_ids |= set(QuizAttempt.objects.values_list('student', flat=True))
        learner_ids |= set(
            User.objects.filter(role=User.Role.STUDENT).values_list('id', flat=True))

        # Nombre de leçons publiées par matière (regroupement matière brute).
        subjects = list(
            Lesson.objects.filter(status='published')
            .values(slug=F('chapter__subject__slug'), name=F('chapter__subject__name'))
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response({
            'members': AlumniProfile.objects.filter(user__status='active').count(),
            'projects': Project.objects.count(),
            'projects_active': Project.objects.filter(status='active').count(),
            'amount_collected': Contribution.objects.filter(status='confirmed').aggregate(
                s=Sum('amount'))['s'] or 0,
            'courses_published': Lesson.objects.filter(status='published').count(),
            'students_reached': len(learner_ids),
            'years': timezone.now().year - FOUNDING_YEAR,
            'subjects': subjects,
        })


class StatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from donations.models import Contribution, PartnershipRequest
        from education.models import Lesson, QuizAttempt
        from events.models import Event
        from projects.models import Project

        contributions = Contribution.objects.filter(status='confirmed')
        attempts = QuizAttempt.objects.all()
        avg_quiz = round(sum(a.percentage for a in attempts) / attempts.count()) if attempts.count() else 0

        return Response({
            'members': {
                'total': User.objects.filter(status='active').count(),
                'pending_validation': User.objects.filter(status='pending').count(),
                'by_role': dict(
                    User.objects.filter(status='active')
                    .values_list('role').annotate(n=Count('id')).order_by()
                ),
            },
            'projects': {
                'active': Project.objects.filter(status='active').count(),
                'budget_total': Project.objects.exclude(status='draft').aggregate(
                    s=Sum('budget'))['s'] or 0,
                'amount_collected': contributions.aggregate(s=Sum('amount'))['s'] or 0,
            },
            'contributions': {
                'confirmed_count': contributions.count(),
                'pending_count': Contribution.objects.filter(status='pending').count(),
                'total_amount': contributions.aggregate(s=Sum('amount'))['s'] or 0,
            },
            'partnerships': {
                'new': PartnershipRequest.objects.filter(status='new').count(),
                'total': PartnershipRequest.objects.count(),
            },
            'education': {
                'courses_published': Lesson.objects.filter(status='published').count(),
                'courses_pending': Lesson.objects.filter(status='pending').count(),
                'quiz_attempts': attempts.count(),
                'quiz_average': avg_quiz,
            },
            'events': {'total': Event.objects.count()},
        })
