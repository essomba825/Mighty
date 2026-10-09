from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .cards import issue_card
from .models import AlumniProfile
from .serializers import AlumniProfileSerializer, MemberCardSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_staff


class AlumniProfileViewSet(viewsets.ModelViewSet):
    """Annuaire des anciens élèves + gestion de son propre profil."""
    serializer_class = AlumniProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = AlumniProfile.objects.select_related('user').filter(user__status='active')
        if not self.request.user.is_authenticated or not self.request.user.is_staff:
            qs = qs.filter(is_visible_in_directory=True)
        return qs

    def perform_create(self, serializer):
        profile = serializer.save(user=self.request.user)
        issue_card(profile)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def issue_card(self, request, pk=None):
        """L'administration délivre ou régénère la carte d'un membre."""
        profile = self.get_object()
        signed_by = request.data.get('signed_by', '')
        force_new = str(request.data.get('force_new', '')).lower() in ('1', 'true', 'yes')
        card = issue_card(profile, signed_by=signed_by, force_new=force_new)
        return Response(MemberCardSerializer(card).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_card(self, request):
        """Carte de membre numérique de l'utilisateur connecté (générée si absente)."""
        profile = getattr(request.user, 'alumni_profile', None)
        if not profile:
            return Response({'detail': "Complétez d'abord votre profil alumni."},
                            status=status.HTTP_404_NOT_FOUND)
        card = issue_card(profile)
        data = MemberCardSerializer(card).data
        data['full_name'] = request.user.get_full_name()
        data['graduation_year'] = profile.graduation_year
        data['profession'] = profile.profession
        data['company'] = profile.company
        data['city'] = profile.city
        data['country'] = profile.country
        data['photo'] = request.build_absolute_uri(profile.photo.url) if profile.photo else None
        return Response(data)
