from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    amount_collected = serializers.SerializerMethodField()
    funds_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'objective', 'budget', 'image',
                  'status', 'amount_collected', 'funds_remaining', 'created_at']

    def get_amount_collected(self, obj):
        from django.db.models import Sum
        return obj.contributions.filter(status='confirmed').aggregate(
            total=Sum('amount'))['total'] or 0

    def get_funds_remaining(self, obj):
        collected = self.get_amount_collected(obj)
        return max(obj.budget - collected, 0)
