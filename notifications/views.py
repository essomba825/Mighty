from django.conf import settings
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, PushSubscription
from .serializers import NotificationSerializer, PushSubscribeSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notifications de l'utilisateur connecté."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'detail': 'Marquée comme lue.'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'detail': 'Toutes marquées comme lues.'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Compteur pour le badge de la cloche (Navbar)."""
        nb = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': nb})

    # --- Web Push -------------------------------------------------------

    @action(detail=False, methods=['get'])
    def push_config(self, request):
        """Clé publique VAPID : le navigateur en a besoin pour s'abonner."""
        return Response({
            'public_key': settings.VAPID_PUBLIC_KEY,
            'enabled': bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY),
        })

    @action(detail=False, methods=['post'])
    def push_subscribe(self, request):
        """Enregistre (ou met à jour) l'abonnement push du navigateur."""
        serializer = PushSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        PushSubscription.objects.update_or_create(
            endpoint=donnees['endpoint'],
            defaults={
                'user': request.user,
                'p256dh': donnees['keys']['p256dh'],
                'auth': donnees['keys']['auth'],
            },
        )
        return Response({'detail': 'Abonnement push actif.'})

    @action(detail=False, methods=['post'])
    def push_unsubscribe(self, request):
        """Retire l'abonnement courant (le membre désactive les poussées)."""
        endpoint = str(request.data.get('endpoint') or '')
        PushSubscription.objects.filter(user=request.user,
                                        endpoint=endpoint).delete()
        return Response({'detail': 'Abonnement push retiré.'})
