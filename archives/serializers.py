from rest_framework import serializers

from .models import ArchiveDocument


class ArchiveDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)

    class Meta:
        model = ArchiveDocument
        fields = ['id', 'title', 'description', 'doc_type', 'file', 'year',
                  'uploaded_by_name', 'is_public', 'created_at']
        read_only_fields = ['uploaded_by_name']
