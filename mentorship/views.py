from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from notifications.models import Notification

from .models import MentorshipOffer, MentorshipRequest
from .serializers import MentorshipOfferSerializer, MentorshipRequestSerializer


class ActiveMemberOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated
                and (request.user.is_staff or request.user.status == 'active'))


class MentorshipOfferViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipOfferSerializer
    permission_classes = [ActiveMemberOnly]

    def get_queryset(self):
        qs = MentorshipOffer.objects.select_related('mentor')
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True) | MentorshipOffer.objects.filter(mentor=self.request.user)
        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(mentor=self.request.user)


class MentorshipRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipRequestSerializer
    permission_classes = [ActiveMemberOnly]

    def get_queryset(self):
        qs = MentorshipRequest.objects.select_related('offer__mentor', 'mentee')
        user = self.request.user
        if user.is_staff:
            return qs
        # Le mentee voit ses demandes ; le mentor voit les demandes reçues
        from django.db.models import Q
        return qs.filter(Q(mentee=user) | Q(offer__mentor=user)).distinct()

    def perform_create(self, serializer):
        request_obj = serializer.save(mentee=self.request.user)
        # Le mentor est notifié en interne (comportement historique).
        try:
            Notification.objects.create(
                user=request_obj.offer.mentor,
                title='Nouvelle demande de mentorat 🤝',
                message=f'{self.request.user.get_full_name()} souhaite être mentoré en '
                        f'"{request_obj.offer.field}".',
                link='/mentorat',
            )
        except Exception:
            pass  # La notification ne doit pas bloquer la création
        # Email au mentée + notification et poussée des admins.
        from notifications.services import apres_demande_mentorat
        apres_demande_mentorat(request_obj)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        obj = self.get_object()
        if obj.offer.mentor != request.user and not request.user.is_staff:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        if obj.status == MentorshipRequest.Status.ACCEPTED:
            return Response({'detail': 'Demande déjà acceptée.'})
        obj.status = MentorshipRequest.Status.ACCEPTED
        obj.save(update_fields=['status'])
        # Email, notification interne et poussée au mentoré (ne lève jamais).
        from notifications.services import apres_mentorat_accepte
        apres_mentorat_accepte(obj)
        return Response({'detail': 'Demande acceptée.'})

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        obj = self.get_object()
        if obj.offer.mentor != request.user and not request.user.is_staff:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        if obj.status == MentorshipRequest.Status.DECLINED:
            return Response({'detail': 'Demande déjà déclinée.'})
        obj.status = MentorshipRequest.Status.DECLINED
        obj.save(update_fields=['status'])
        # Email, notification interne et poussée au mentoré (ne lève jamais).
        from notifications.services import apres_mentorat_decline
        apres_mentorat_decline(obj)
        return Response({'detail': 'Demande déclinée.'})
