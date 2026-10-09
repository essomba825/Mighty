from django.conf import settings
from django.db import models


class Project(models.Model):
    """Projet de l'association à financer (éducatif, communautaire...)."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        ACTIVE = 'active', 'En collecte'
        FUNDED = 'funded', 'Financé'
        COMPLETED = 'completed', 'Réalisé'

    title = models.CharField(max_length=200)
    description = models.TextField()
    objective = models.TextField(verbose_name="Objectif")
    budget = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Budget estimé (FCFA)")
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name='projects_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def amount_collected(self):
        from django.db.models import Sum
        return self.contributions.aggregate(total=Sum('amount'))['total'] or 0

    def __str__(self):
        return self.title
