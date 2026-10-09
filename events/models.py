from django.conf import settings
from django.db import models


class Event(models.Model):
    """Événement de l'association (réunion, cérémonie, activité...)."""

    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200, verbose_name="Lieu")
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, related_name='organized_events')
    is_public = models.BooleanField(default=True, verbose_name="Visible publiquement")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.title} ({self.date:%d/%m/%Y})'


class EventRegistration(models.Model):
    """Inscription d'un membre à un événement."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
