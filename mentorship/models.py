from django.conf import settings
from django.db import models


class MentorshipOffer(models.Model):
    """Offre de mentorat publiée par un ancien élève."""

    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='mentorship_offers')
    field = models.CharField(max_length=150, verbose_name="Domaine (ex: Ingénierie, Médecine...)")
    description = models.TextField(verbose_name="Ce que je propose")
    availability = models.CharField(max_length=150, blank=True, verbose_name="Disponibilités")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.field} — {self.mentor.get_full_name()}'


class MentorshipRequest(models.Model):
    """Demande de mentorat d'un membre/élève à un mentor."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACCEPTED = 'accepted', 'Acceptée'
        DECLINED = 'declined', 'Déclinée'

    offer = models.ForeignKey(MentorshipOffer, on_delete=models.CASCADE,
                              related_name='requests')
    mentee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='mentorship_requests')
    message = models.TextField(verbose_name="Ma demande")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('offer', 'mentee')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mentee} -> {self.offer}'