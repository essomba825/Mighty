from django.db import models


class ContactInfo(models.Model):
    """Coordonnées de l'association, modifiables depuis l'admin.

    Une seule ligne en base (singleton) : la vue de contact la lit et la sert
    telle quelle au front. Champs bilingues pour l'adresse et l'accueil."""
    email = models.EmailField(default='contact@megamightysixers.org')
    phone = models.CharField(max_length=30, blank=True,
                             default='+237 600 00 00 00')
    whatsapp = models.CharField(max_length=200, blank=True,
                                default='https://wa.me/237600000000')
    address_en = models.CharField(max_length=200, blank=True, default='Cameroon')
    address_fr = models.CharField(max_length=200, blank=True, default='Cameroun')
    hours_en = models.CharField(max_length=200, blank=True,
                                default='Monday to Saturday, 9 am — 5 pm')
    hours_fr = models.CharField(max_length=200, blank=True,
                                default='Lundi au samedi, 9 h — 17 h')
    facebook = models.URLField(blank=True, default='https://facebook.com/megamightysixers')
    twitter = models.URLField(blank=True, default='https://twitter.com/megamightysixers')
    instagram = models.URLField(blank=True, default='https://instagram.com/megamightysixers')
    youtube = models.URLField(blank=True, default='https://youtube.com/@megamightysixers')

    class Meta:
        verbose_name = 'Informations de contact'
        verbose_name_plural = 'Informations de contact'

    def __str__(self):
        return self.email

    @classmethod
    def load(cls):
        """Ligne unique de l'association, creee avec les valeurs par defaut si
        absente (premiere base, base fraichement clonée...)."""
        info, _ = cls.objects.get_or_create(pk=1)
        return info


class ContactMessage(models.Model):
    """Message envoye depuis la page contact, consulte dans l'admin."""
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False, verbose_name='Lu')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.subject or self.email}'