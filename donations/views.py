from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Contribution, PartnershipRequest
from .serializers import ContributionSerializer, PartnershipRequestSerializer


class ContributionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                          mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                          viewsets.GenericViewSet):
    """Déclaration d'une contribution (paiement hors plateforme, confirmée par admin).
    Un admin voit tout ; un membre connecté voit ses propres contributions.

    §6 : « Management and monitoring of donations and project-support records »
    PATCH /api/donations/contributions/<id>/ permet à l'admin de confirmer ou rejeter.
    """
    serializer_class = ContributionSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ('update', 'partial_update'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Contribution.objects.select_related('project', 'donor')
        if self.request.user.is_staff:
            return qs
        return qs.filter(donor=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(donor=user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def confirm(self, request, pk=None):
        """Raccourci : confirme directement sans PATCH complet."""
        contribution = self.get_object()
        contribution.status = 'confirmed'
        contribution.save()
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Raccourci : rejette directement sans PATCH complet."""
        contribution = self.get_object()
        contribution.status = 'rejected'
        contribution.save()
        return Response({'status': 'rejected'})


class PartnershipRequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                                mixins.UpdateModelMixin,
                                viewsets.GenericViewSet):
    """Demandes de partenariat : dépôt public, consultation et traitement réservés aux admins.

    §6 : l'admin peut mettre à jour le statut d'une demande (contacted, accepted, refused).
    """
    serializer_class = PartnershipRequestSerializer
    queryset = PartnershipRequest.objects.select_related('project')

    def get_permissions(self):
        if self.action in ('create', 'status'):
            return [permissions.AllowAny()]
        if self.action in ('update', 'partial_update'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        """Une seule demande en cours par email : les doublons sont rejetés
        tant que la précédente n'est pas traitée (acceptée ou refusée)."""
        email = (request.data.get('email') or (request.user.email if request.user and request.user.is_authenticated else '')).strip().lower()
        if not email:
            return Response({'detail': "Email requis."}, status=status.HTTP_400_BAD_REQUEST)
        if PartnershipRequest.objects.filter(
                email__iexact=email, status__in=['new', 'contacted']).exists():
            return Response(
                {'detail': "Une demande de partenariat avec cet email est déjà "
                           "en cours de traitement. L'association vous répondra "
                           "sous 72 h avant d'en soumettre une nouvelle."},
                status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.save()
        # Notifier l'utilisateur par notification interne + push s'il possède un compte
        from django.contrib.auth import get_user_model
        from notifications.models import Notification
        
        User = get_user_model()
        user = User.objects.filter(email__iexact=instance.email).first()
        if user:
            status_messages = {
                'accepted': ('Partenariat validé ! 🎉', 'Votre demande de partenariat a été acceptée par l\'association. Nous vous recontacterons très prochainement pour finaliser les détails.'),
                'contacted': ('Demande de partenariat en cours d\'étude', 'Votre proposition de partenariat est actuellement en cours d\'examen par notre équipe.'),
                'refused': ('Mise à jour concernant votre partenariat', 'Votre demande de partenariat a été examinée par notre équipe.'),
            }
            if instance.status in status_messages:
                title, msg = status_messages[instance.status]
                if not Notification.objects.filter(user=user, title=title, message=msg).exists():
                    Notification.objects.create(
                        user=user,
                        title=title,
                        message=msg,
                        link='/partenaires'
                    )
                    try:
                        from notifications.push import envoyer_push_utilisateur
                        envoyer_push_utilisateur(user, title, msg, link='/partenaires')
                    except Exception:
                        pass

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def status(self, request):
        """Suivi public / membre : état de la dernière demande pour un email donné."""
        email = (request.query_params.get('email') or (request.user.email if request.user and request.user.is_authenticated else '')).strip().lower()
        if not email:
            return Response({'detail': 'Email requis.'}, status=400)
        demande = (PartnershipRequest.objects.filter(email__iexact=email)
                   .order_by('-created_at').first())
        if not demande:
            return Response({'exists': False})
        return Response({
            'exists': True,
            'status': demande.status,
            'status_label': demande.get_status_display(),
            'organization': demande.organization or demande.contact_name,
            'created_at': demande.created_at,
            'pending': demande.status in ('new', 'contacted'),
        })
