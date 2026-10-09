from rest_framework import serializers

from .models import ContactInfo, ContactMessage


class ContactInfoSerializer(serializers.ModelSerializer):
    address = serializers.SerializerMethodField()
    hours = serializers.SerializerMethodField()
    social = serializers.SerializerMethodField()

    class Meta:
        model = ContactInfo
        fields = ['email', 'phone', 'whatsapp', 'address', 'hours', 'social']

    def get_address(self, obj):
        return {
            'en': obj.address_en or 'Cameroon',
            'fr': obj.address_fr or 'Cameroun',
        }

    def get_hours(self, obj):
        return {
            'en': obj.hours_en,
            'fr': obj.hours_fr,
        }

    def get_social(self, obj):
        """Liste des reseaux remplis, dans un ordre stable. Le front connait
        l'icone et la couleur de chaque cle ; une cle vide est omise."""
        liens = [
            ('facebook', obj.facebook),
            ('twitter', obj.twitter),
            ('instagram', obj.instagram),
            ('youtube', obj.youtube),
            ('whatsapp', obj.whatsapp),
        ]
        return [{'key': cle, 'url': url} for cle, url in liens if url]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']