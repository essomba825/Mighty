from django.conf import settings
from django.db import models


class AlumniProfile(models.Model):
    """Profil d'un ancien élève."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='alumni_profile')
    graduation_year = models.PositiveIntegerField(verbose_name="Année de promotion")
    profession = models.CharField(max_length=150, blank=True)
    company = models.CharField(max_length=150, blank=True, verbose_name="Entreprise")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    country = models.CharField(max_length=100, blank=True, default='Cameroun', verbose_name="Pays")
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=255, blank=True, verbose_name="Compétences")
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_visible_in_directory = models.BooleanField(default=True, verbose_name="Visible dans l'annuaire")

    def __str__(self):
        return f'{self.user.get_full_name()} - Promotion {self.graduation_year}'


class MemberCard(models.Model):
    """Carte de membre numérique, délivrée par l'administration."""

    profile = models.OneToOneField(AlumniProfile, on_delete=models.CASCADE,
                                   related_name='member_card')
    card_number = models.CharField(max_length=20, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(verbose_name="Valide jusqu'au")
    is_active = models.BooleanField(default=True)
    signed_by = models.CharField(max_length=120, blank=True,
                                 verbose_name="Signataire", help_text="Ex. Président de l'association")
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True,
                                  verbose_name="Signature (tampon ou signature)")

    def __str__(self):
        return f'Carte {self.card_number} — {self.profile.user.get_full_name()}'
