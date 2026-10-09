import re
import uuid

from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from donations.models import Contribution
from notifications.services import apres_paiement_confirme

from .models import Payment, PaymentRequest
from .providers import get_provider
from .serializers import (
    PaymentInitiateSerializer,
    PaymentRequestSerializer,
    PaymentRequestVerifySerializer,
    PaymentSerializer,
)


def _normalise_telephone(raw):
    """Numéro camerounais sous forme nationale : +237699000000 et 699000000 -> 699000000."""
    digits = re.sub(r'\D', '', raw or '')
    return digits[3:] if digits.startswith('237') and len(digits) == 12 else digits


class PaymentRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """Demandes de paiement à la SaveNow : génération de référence, compteur
    journalier, config marchand, création puis vérification par code."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentRequestSerializer

    def get_queryset(self):
        qs = PaymentRequest.objects.select_related('project', 'contribution', 'user')
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def reference(self, request):
        """payment_ref généré côté serveur (source de vérité, comme SaveNow)."""
        return Response({'reference': f'MMS-{uuid.uuid4().hex[:12].upper()}'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def config(self, request):
        """Informations publiques pour composer le code USSD côté téléphone."""
        return Response({
            'beneficiary': settings.PAYMENT_BENEFICIARY,
            'daily_limit': settings.PAYMENT_DAILY_LIMIT,
            'min_amount': settings.PAYMENT_MIN_AMOUNT,
            'simulation': settings.PAYMENT_SIMULATION,
            'mtn_momo': {'merchant_code': settings.MERCHANT_MTN_CODE},
            'orange_money': {'merchant_code': settings.MERCHANT_ORANGE_CODE},
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def total(self, request):
        """Combien de demandes du jour reste-t-il ?

        Comptées les demandes passées hors « opened » (une simple ouverture ne
        consomme pas la limite). Pour un utilisateur connecté on filtre par
        (user, projet) ; sinon par (téléphone, projet)."""
        limite = settings.PAYMENT_DAILY_LIMIT
        project_id = request.query_params.get('project')
        qs = PaymentRequest.objects.exclude(status=PaymentRequest.RequestStatus.OPENED)
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
            phone = _normalise_telephone(request.query_params.get('phone'))
            if phone:
                qs = qs.filter(phone_number=phone)
        else:
            phone = _normalise_telephone(request.query_params.get('phone'))
            if not phone:
                return Response({'total_requests': 0, 'limit': limite})
            qs = qs.filter(phone_number=phone)
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = qs.filter(created_at__date=timezone.localdate())
        return Response({'total_requests': qs.count(), 'limit': limite})

    def create(self, request):
        """Crée la contribution (pending) + la demande de paiement (initiated).

        Retourne le contrat SaveNow : {valid, text/code, ...} pour un
        mappage propre côté front."""
        limites = settings.PAYMENT_DAILY_LIMIT

        def ko(code, detail, champ=None, http=status.HTTP_400_BAD_REQUEST):
            payload = {'valid': False, 'detail': detail, 'text': code}
            if champ:
                payload['field'] = champ
            return Response(payload, status=http)

        data = request.data
        ref = (data.get('payment_ref') or '').strip()
        if not ref:
            ref = f'MMS-{uuid.uuid4().hex[:12].upper()}'
            for _ in range(5):
                if not PaymentRequest.objects.filter(payment_ref=ref).exists():
                    break
                ref = f'MMS-{uuid.uuid4().hex[:12].upper()}'
        project_id = data.get('project')
        nom = (data.get('donor_name') or '').strip()
        email = (data.get('donor_email') or '').strip()
        message = (data.get('message') or '').strip()
        telephone = (data.get('phone_number') or '').strip()
        operateur = (data.get('provider') or '').strip()
        telephone_normalise = _normalise_telephone(telephone)
        try:
            montant = int(data.get('amount'))
        except (TypeError, ValueError):
            montant = 0

        if not project_id:
            return ko('project_missing', 'Projet requis.', champ='project')
        if PaymentRequest.objects.filter(payment_ref=ref).exists():
            return ko('payment_ref_used', 'Référence de paiement déjà utilisée.',
                      champ='payment_ref')
        if not nom:
            return ko('donor_name_missing', 'Votre nom est requis.', champ='donor_name')
        if '@' not in email or '.' not in email.split('@')[-1]:
            return ko('donor_email_invalid', 'Adresse email invalide.', champ='donor_email')
        if montant < settings.PAYMENT_MIN_AMOUNT:
            return ko('invalid_amount',
                      f'Montant minimum : {settings.PAYMENT_MIN_AMOUNT} FCFA.', champ='amount')
        if not re.match(r'^6\d{8}$', telephone_normalise):
            return ko('invalid_phone', 'Numéro Mobile Money invalide.', champ='phone_number')
        if operateur not in (Payment.Provider.MTN, Payment.Provider.ORANGE):
            return ko('invalid_operator', 'Opérateur invalide.', champ='provider')

        aujourd = timezone.localdate()
        compteur = (PaymentRequest.objects
                    .exclude(status=PaymentRequest.RequestStatus.OPENED)
                    .filter(user=request.user, project_id=project_id,
                            created_at__date=aujourd)
                    .count())
        if compteur >= limites:
            return ko('limit_reached',
                      f'Limite de {limites} demandes par jour atteinte.', http=429)

        contribution = Contribution.objects.create(
            project_id=project_id,
            donor=request.user,
            donor_name=nom,
            donor_email=email,
            amount=montant,
            method=operateur,
            message=message,
        )
        demande = PaymentRequest.objects.create(
            payment_ref=ref,
            project_id=project_id,
            user=request.user,
            amount=montant,
            phone_number=telephone_normalise,
            provider=operateur,
            status=PaymentRequest.RequestStatus.INITIATED,
            contribution=contribution,
        )
        return Response({
            'valid': True,
            'code': 'request_created',
            'payment_request_id': demande.id,
            'reference': demande.payment_ref,
            'contribution_id': contribution.id,
            'amount': str(demande.amount),
            'provider': demande.provider,
            'phone_number': demande.phone_number,
            'status': demande.status,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Vérifie le code de transaction reçu par SMS (composé via USSD).

        En simulation, tout code d'au moins 4 caractères est accepté. La
        contribution passe à 'confirmed' et une notification est envoyée."""
        demande = self.get_object()
        if demande.status == PaymentRequest.RequestStatus.VERIFIED:
            return Response({'valid': True, 'code': 'already_verified',
                             'reference': demande.payment_ref,
                             'transaction_code': demande.transaction_code})
        if demande.status != PaymentRequest.RequestStatus.INITIATED:
            return Response({'valid': False, 'text': 'not_initiated',
                             'detail': 'Cette demande n’est pas en attente de vérification.'},
                            status=status.HTTP_400_BAD_REQUEST)

        verif = PaymentRequestVerifySerializer(data=request.data)
        if not verif.is_valid():
            return Response({'valid': False, 'text': 'invalid_code',
                             'field': 'transaction_code',
                             'detail': 'Code de transaction invalide.'},
                            status=status.HTTP_400_BAD_REQUEST)
        code = verif.validated_data['transaction_code']

        provider = get_provider(demande.provider)
        verifie = provider.verify(demande, code)

        if not verifie:
            demande.status = PaymentRequest.RequestStatus.FAILED
            demande.save(update_fields=['status'])
            return Response({'valid': False, 'text': 'invalid_code',
                             'detail': 'Le code de transaction est invalide.'},
                            status=status.HTTP_400_BAD_REQUEST)

        demande.transaction_code = code
        demande.status = PaymentRequest.RequestStatus.VERIFIED
        demande.verified_at = timezone.now()
        demande.save()

        contribution = demande.contribution
        if contribution:
            if not hasattr(contribution, 'payment'):
                Payment.objects.create(
                    contribution=contribution,
                    provider=demande.provider or Payment.Provider.MTN,
                    phone_number=demande.phone_number or '',
                    amount=demande.amount,
                    reference=f'MMS-{uuid.uuid4().hex[:12].upper()}',
                    status=Payment.Status.SUCCESS,
                )
            contribution.status = 'confirmed'
            contribution.save(update_fields=['status'])
            # Notification du donateur + reçu email + alerte des admins
            # (notification interne et poussée web).
            apres_paiement_confirme(
                utilisateur=demande.user,
                montant=demande.amount,
                projet=demande.project.title if demande.project else '',
                reference=demande.payment_ref,
                email=contribution.donor_email if contribution else None,
            )

        return Response({'valid': True, 'code': 'verified',
                         'reference': demande.payment_ref,
                         'transaction_code': code})


class PaymentViewSet(viewsets.GenericViewSet):
    """Compatibilité : POST /api/payments/ initie un paiement pour une
    contribution déjà créée. Conservé tel quel pour smoke_test et l'export."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Payment.objects.select_related('contribution__project', 'contribution__donor')
        if self.request.user.is_staff:
            return qs
        return qs.filter(contribution__donor=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentInitiateSerializer
        return PaymentSerializer

    def list(self, request):
        return Response(PaymentSerializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(PaymentSerializer(self.get_object()).data)

    def create(self, request):
        """Initie un paiement Mobile Money pour une contribution."""
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contribution = serializer.validated_data['contribution']

        payment = Payment.objects.create(
            contribution=contribution,
            provider=serializer.validated_data['provider'],
            phone_number=serializer.validated_data['phone_number'],
            amount=contribution.amount,
            reference=f'MMS-{uuid.uuid4().hex[:12].upper()}',
        )

        provider = get_provider(payment.provider)
        response = provider.initiate(payment)
        payment.provider_response = response
        if provider.is_success(response):
            payment.status = Payment.Status.SUCCESS
            contribution.status = 'confirmed'
            contribution.save(update_fields=['status'])
            # Reçu + notification + poussée (donateur et admins).
            apres_paiement_confirme(
                utilisateur=contribution.donor,
                montant=payment.amount,
                projet=contribution.project.title if contribution.project else '',
                reference=payment.reference,
                email=contribution.donor_email,
            )
        else:
            payment.status = Payment.Status.FAILED
        payment.save()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def callback(self, request, pk=None):
        """Callback du provider (production). En simulation : vérifie l'état."""
        payment = self.get_object()
        provider = get_provider(payment.provider)
        if provider.is_success(payment.provider_response or {}):
            # Si la contribution était déjà confirmée (par create/verify),
            # on ne rediffuse pas les notifications.
            deja_confirmee = payment.contribution.status == 'confirmed'
            payment.status = Payment.Status.SUCCESS
            payment.contribution.status = 'confirmed'
            payment.contribution.save(update_fields=['status'])
            payment.save(update_fields=['status'])
            if not deja_confirmee:
                apres_paiement_confirme(
                    utilisateur=payment.contribution.donor,
                    montant=payment.amount,
                    projet=(payment.contribution.project.title
                            if payment.contribution.project else ''),
                    reference=payment.reference,
                    email=payment.contribution.donor_email,
                )
        return Response({'status': payment.status})