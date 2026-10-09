from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Utilisateur de la plateforme avec rôles et validation par admin."""

    class Role(models.TextChoices):
        ALUMNI = 'alumni', 'Ancien élève'
        STUDENT = 'student', 'Élève'
        TEACHER = 'teacher', 'Enseignant'
        PARTNER = 'partner', 'Partenaire / Donateur'
        ADMIN = 'admin', 'Administrateur'

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente de validation'
        ACTIVE = 'active', 'Actif'
        REJECTED = 'rejected', 'Rejeté'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ALUMNI)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f'{self.get_full_name() or self.email} ({self.get_role_display()})'


class ActivityLog(models.Model):
    """Journal d'activite (§9 : « access controls and activity logging »).

    Ce n'est pas le log technique de Django : c'est la trace lisible par
    l'administration que le cahier des charges demande, celle qui repond a la
    seule question qui compte apres un incident — « qui a fait quoi, sur quel
    objet, et depuis ou ? ».

    Une seule table, volontairement. Un journal par application multiplierait
    les migrations et les oublis.

    `actor_label` recopie le nom au moment de l'action : si le compte est
    supprime plus tard, la ligne reste lisible. C'est le point d'un journal.
    """

    class Action(models.TextChoices):
        CREATE = 'create', 'Creation'
        UPDATE = 'update', 'Modification'
        DELETE = 'delete', 'Suppression'
        LOGIN = 'login', 'Connexion'
        VALIDATE = 'validate', 'Validation'
        REJECT = 'reject', 'Rejet'
        PUBLISH = 'publish', 'Publication'
        BACKUP = 'backup', 'Sauvegarde'

    actor = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='activity_logs')
    actor_label = models.CharField(
        max_length=150, blank=True,
        help_text='Nom copie au moment de l action : le journal reste lisible '
                  'meme si le compte est supprime ensuite.')
    action = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Entree de journal'
        verbose_name_plural = 'Journal d activite'
        indexes = [models.Index(fields=['model_name', 'object_id'])]

    def __str__(self):
        who = self.actor_label or (str(self.actor) if self.actor else 'systeme')
        return f'{self.created_at:%Y-%m-%d %H:%M} {who} : {self.summary or self.action}'
