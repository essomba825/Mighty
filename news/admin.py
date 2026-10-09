from django.contrib import admin

from .models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published', 'published_at')
    list_filter = ('published',)
    search_fields = ('title', 'content')
