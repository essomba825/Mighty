from rest_framework import serializers

from .models import MentorshipOffer, MentorshipRequest


class MentorshipOfferSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source='mentor.get_full_name', read_only=True)
    requests_count = serializers.IntegerField(source='requests.count', read_only=True)

    class Meta:
        model = MentorshipOffer
        fields = ['id', 'mentor_name', 'field', 'description', 'availability',
                  'is_active', 'requests_count', 'created_at']
        read_only_fields = ['requests_count']


class MentorshipRequestSerializer(serializers.ModelSerializer):
    mentee_name = serializers.CharField(source='mentee.get_full_name', read_only=True)
    offer_title = serializers.CharField(source='offer.field', read_only=True)

    class Meta:
        model = MentorshipRequest
        fields = ['id', 'offer', 'offer_title', 'mentee_name', 'message',
                  'status', 'created_at']
        read_only_fields = ['status']
