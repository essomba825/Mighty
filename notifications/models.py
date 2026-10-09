from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notification interne pour un utilisateur (compte validé, nouvel événement, etc.)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True, verbose_name="Lien (optionnel)")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} -> {self.user}'


class PushSubscription(models.Model):
    """Abonnement Web Push d'un navigateur (Push API + VAPID).

    Créé par POST /api/notifications/push_subscribe/ quand le membre accepte
    les notifications. Un abonnement mort (404/410 du service de push) est
    supprimé automatiquement lors du prochain envoi.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=128, verbose_name='Clé p256dh')
    auth = models.CharField(max_length=128, verbose_name='Clé auth')
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        return f'push de {self.user} ({self.endpoint[:60]})'
