from django.conf import settings
from django.db import models


class ArchiveDocument(models.Model):
    """Document historique : photo, PDF, vidéo, souvenir..."""

    class DocType(models.TextChoices):
        PHOTO = 'photo', 'Photo'
        VIDEO = 'video', 'Vidéo'
        PDF = 'pdf', 'Document PDF'
        OTHER = 'other', 'Autre'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    doc_type = models.CharField(max_length=10, choices=DocType.choices, default=DocType.PHOTO)
    file = models.FileField(upload_to='archives/')
    year = models.PositiveIntegerField(blank=True, null=True, verbose_name="Année")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='archives_uploaded')
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-created_at']

    def __str__(self):
        return self.title
