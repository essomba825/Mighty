from rest_framework import serializers

from .models import AlumniProfile, MemberCard


class MemberCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberCard
        fields = ['card_number', 'issued_at', 'valid_until', 'is_active', 'signed_by', 'signature']


class AlumniProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    member_card = MemberCardSerializer(read_only=True)

    class Meta:
        model = AlumniProfile
        fields = ['id', 'full_name', 'email', 'graduation_year', 'profession', 'company',
                  'city', 'country', 'bio', 'skills', 'photo', 'is_visible_in_directory',
                  'member_card']
