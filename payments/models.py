from django.conf import settings
from django.db import models

from projects.models import Project


class Payment(models.Model):
    """Paiement Mobile Money lié à une contribution.

    Mode par défaut : SIMULATION (validation auto en dev).
    Pour la production : configurer MTN_MOMO_* / ORANGE_MONEY_* dans les
    variables d'environnement et brancher le provider correspondant."""

    class Provider(models.TextChoices):
        MTN = 'mtn_momo', 'MTN Mobile Money'
        ORANGE = 'orange_money', 'Orange Money'

    class Status(models.TextChoices):
        INITIATED = 'initiated', 'Initié'
        SUCCESS = 'success', 'Réussi'
        FAILED = 'failed', 'Échoué'
        CANCELLED = 'cancelled', 'Annulé'

    contribution = models.OneToOneField('donations.Contribution', on_delete=models.CASCADE,
                                        related_name='payment')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    phone_number = models.CharField(max_length=20, verbose_name="Numéro Mobile Money")
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    reference = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INITIATED)
    provider_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.reference} — {self.amount} FCFA ({self.get_status_display()})'


class PaymentRequest(models.Model):
    """Demande de paiement Mobile Money, calquée sur le flux SaveNow de PettyCash.

    Cycle : opened (payment_ref généré) -> initiated (l'utilisateur confirme et
    compose le code USSD) -> verified (code de transaction saisi et validé).
    Un maximum de PAYMENT_DAILY_LIMIT demandes « initiées » par jour et par
    (utilisateur, projet) est accepté ; les demandes seulement ouvertes ne
    comptent pas dans la limite."""

    class RequestStatus(models.TextChoices):
        OPENED = 'opened', 'Ouverte'
        INITIATED = 'initiated', 'Initiée'
        VERIFIED = 'verified', 'Vérifiée'
        FAILED = 'failed', 'Échouée'

    payment_ref = models.CharField(max_length=50, unique=True, verbose_name="Référence de paiement")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True,
                                related_name='payment_requests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                             blank=True, related_name='payment_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Montant (FCFA)")
    phone_number = models.CharField(max_length=20, blank=True, default='',
                                    verbose_name="Numéro Mobile Money")
    provider = models.CharField(max_length=20, blank=True, default='',
                                choices=Payment.Provider.choices)
    status = models.CharField(max_length=10, choices=RequestStatus.choices,
                              default=RequestStatus.OPENED)
    transaction_code = models.CharField(max_length=100, blank=True,
                                        verbose_name="Code de transaction")
    contribution = models.OneToOneField('donations.Contribution', on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        related_name='payment_request')
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'project', 'created_at']),
            models.Index(fields=['phone_number', 'project', 'created_at']),
        ]

    def __str__(self):
        return f'{self.payment_ref} — {self.amount} FCFA ({self.get_status_display()})'
