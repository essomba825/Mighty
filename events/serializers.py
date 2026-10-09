from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source='organizer.get_full_name', read_only=True)
    registrations_count = serializers.IntegerField(source='registrations.count', read_only=True)
    is_registered = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'date', 'location', 'image',
                  'organizer_name', 'registrations_count', 'is_registered',
                  'is_public', 'created_at']
        read_only_fields = ['organizer_name']

    def get_is_registered(self, obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and obj.registrations.filter(user=user).exists())
