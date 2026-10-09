from rest_framework import serializers

from .models import Notification, PushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'link', 'is_read', 'created_at']
        read_only_fields = ['title', 'message', 'link']


class PushKeysSerializer(serializers.Serializer):
    """Clés d'encryption d'un abonnement Push (format Push API du navigateur)."""
    p256dh = serializers.CharField(max_length=128)
    auth = serializers.CharField(max_length=128)


class PushSubscribeSerializer(serializers.Serializer):
    """Charge utile de pushManager.subscribe() : {endpoint, keys, ...}."""
    endpoint = serializers.URLField(max_length=500)
    keys = PushKeysSerializer()
    expirationTime = serializers.IntegerField(required=False, allow_null=True)
