from rest_framework import serializers

from .models import NewsArticle


class NewsArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = NewsArticle
        fields = ['id', 'title', 'content', 'image', 'author_name',
                  'published', 'published_at', 'created_at']
