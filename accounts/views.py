from django.contrib.auth import get_user_model
from rest_framework import filters, generics, mixins, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .journal import record
from .serializers import AdminUserSerializer, LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Journalise uniquement les succes. `super().post` leve sur identifiants
        # faux, donc le code ci-dessous n'est atteint qu'en cas de succes, et
        # aucune ligne ne vient enregistrer la tentative d'un tiers.
        if response.status_code == 200:
            # `request.user` est encore anonyme ici : la vue est en AllowAny et
            # l'authentification vient d'aboutir. Il faut donc retrouver la
            # personne a partir de l'identifiant saisi, sinon l'entree reste
            # orpheline et le journal ne dit pas QUI s'est connecte.
            identifiant = (request.data.get('identifier')
                           or request.data.get('email') or '')
            acteur = (User.objects.filter(email__iexact=identifiant).first()
                      or User.objects.filter(username__iexact=identifiant).first())
            record(request, action='login', model_name='User',
                   object_id=acteur.pk if acteur else '',
                   summary=f'Connexion reussie ({identifiant})',
                   actor=acteur)
        return response


class RegisterView(generics.CreateAPIView):
    """Inscription : le compte est créé en statut 'pending' (validation admin requise)."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        utilisateur = serializer.save()
        # Email de bienvenue + alerte des admins (notification + push).
        # `apres_inscription` n'élève jamais : la réponse HTTP reste propre.
        from notifications.services import apres_inscription
        apres_inscription(utilisateur)


class MeView(APIView):
    """Profil de l'utilisateur connecté."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminUserViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """Gestion des utilisateurs réservée aux administrateurs (§6).

    §6 : « User and role management » sans passer par l'Admin Django.
    Seuls les champs `role`, `status` et `is_staff` sont modifiables via PATCH
    (les autres sont en lecture seule dans AdminUserSerializer).

    Endpoints :
    - GET   /api/auth/admin/users/          — liste, filtre par ?status= ?role=
    - GET   /api/auth/admin/users/<id>/     — détail
    - PATCH /api/auth/admin/users/<id>/     — modifier role / status / is_staff
    """
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_login', 'status', 'role']
    ordering = ['-date_joined']

    def get_queryset(self):
        qs = User.objects.all()
        status_filter = self.request.query_params.get('status')
        role_filter   = self.request.query_params.get('role')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if role_filter:
            qs = qs.filter(role=role_filter)
        return qs

    def perform_update(self, serializer):
        ancien        = self.get_object()
        ancien_status = ancien.status
        ancien_role   = ancien.role
        utilisateur   = serializer.save()

        # Journalise et notifie les changements significatifs
        if utilisateur.status != ancien_status:
            action = 'validate' if utilisateur.status == 'active' else 'reject'
            record(self.request, action=action, model_name='User',
                   object_id=utilisateur.pk,
                   summary=f'{utilisateur.get_full_name()} : {ancien_status} → {utilisateur.status}')
            self._notifier(utilisateur)
        elif utilisateur.role != ancien_role:
            record(self.request, action='update', model_name='User',
                   object_id=utilisateur.pk,
                   summary=f'{utilisateur.get_full_name()} : rôle {ancien_role} → {utilisateur.role}')

    def _notifier(self, utilisateur):
        """Crée une notification interne selon le nouveau statut du compte."""
        try:
            from notifications.models import Notification
            if utilisateur.status == 'active':
                Notification.objects.create(
                    user=utilisateur,
                    title='Compte validé',
                    message='Votre compte a été validé par un administrateur. '
                            'Vous pouvez maintenant accéder à votre espace membre.',
                    link='/espace-membre',
                )
            elif utilisateur.status == 'rejected':
                Notification.objects.create(
                    user=utilisateur,
                    title='Compte non validé',
                    message="Votre demande d'adhésion n'a pas pu être acceptée. "
                            "Contactez l'association pour plus d'informations.",
                    link='/contact',
                )
        except Exception:
            pass  # La notification est un bonus ; elle ne doit pas bloquer la réponse
