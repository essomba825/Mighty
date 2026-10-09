from rest_framework import serializers

from .models import Contribution, PartnershipRequest


class ContributionSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = Contribution
        fields = ['id', 'project', 'project_title', 'donor_name', 'donor_email',
                  'amount', 'method', 'status', 'message', 'created_at']
        read_only_fields = ['status']


class PartnershipRequestSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = PartnershipRequest
        fields = ['id', 'organization', 'contact_name', 'email', 'phone',
                  'partner_type', 'project', 'project_title', 'message',
                  'status', 'created_at']
        read_only_fields = ['status']
        extra_kwargs = {'organization': {'required': False, 'allow_blank': True}}
