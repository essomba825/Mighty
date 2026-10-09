from django.conf import settings
from django.db import models

from projects.models import Project


class Contribution(models.Model):
    """Contribution financière enregistrée (le paiement se fait hors plateforme en Phase 1-2)."""

    class Method(models.TextChoices):
        MTN = 'mtn_momo', 'MTN Mobile Money'
        ORANGE = 'orange_money', 'Orange Money'
        BANK = 'bank', 'Virement bancaire'
        CASH = 'cash', 'Espèces'
        OTHER = 'other', 'Autre'

    class Status(models.TextChoices):
        PENDING = 'pending', 'À confirmer'
        CONFIRMED = 'confirmed', 'Confirmée'
        REJECTED = 'rejected', 'Rejetée'

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                related_name='contributions', blank=True, null=True)
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='contributions')
    donor_name = models.CharField(max_length=150, verbose_name="Nom du donateur")
    donor_email = models.EmailField(verbose_name="Email du donateur")
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Montant (FCFA)")
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.MTN)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.donor_name} — {self.amount} FCFA'


class PartnershipRequest(models.Model):
    """Demande de partenariat / sponsoring envoyée par une organisation."""

    class PartnerType(models.TextChoices):
        COMPANY = 'company', 'Entreprise'
        NGO = 'ngo', 'ONG / Association'
        INDIVIDUAL = 'individual', 'Particulier'
        PUBLIC = 'public', 'Institution publique'

    class Status(models.TextChoices):
        NEW = 'new', 'Nouvelle'
        CONTACTED = 'contacted', 'Contactée'
        ACCEPTED = 'accepted', 'Acceptée'
        REFUSED = 'refused', 'Refusée'

    organization = models.CharField(max_length=200, blank=True, default='',
                                    verbose_name="Organisation (facultatif)")
    contact_name = models.CharField(max_length=150, verbose_name="Personne de contact")
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    partner_type = models.CharField(max_length=20, choices=PartnerType.choices)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='partnership_requests')
    message = models.TextField(verbose_name="Proposition")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.organization or self.contact_name} ({self.get_partner_type_display()})'
