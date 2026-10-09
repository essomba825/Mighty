from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Event, EventRegistration
from .serializers import EventSerializer


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Event.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_public=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, pk=None):
        """Inscription du membre connecté à l'événement."""
        event = self.get_object()
        _, created = EventRegistration.objects.get_or_create(event=event, user=request.user)
        if not created:
            return Response({'detail': 'Déjà inscrit.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Inscription confirmée.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unregister(self, request, pk=None):
        """Annulation de l'inscription du membre connecté."""
        event = self.get_object()
        deleted, _ = EventRegistration.objects.filter(event=event, user=request.user).delete()
        if not deleted:
            return Response({'detail': "Vous n'êtes pas inscrit."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Inscription annulée.'})
