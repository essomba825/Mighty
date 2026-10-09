from django.utils import timezone
from rest_framework import permissions, viewsets

from .models import NewsArticle
from .serializers import NewsArticleSerializer


class NewsArticleViewSet(viewsets.ModelViewSet):
    serializer_class = NewsArticleSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = NewsArticle.objects.select_related('author')
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(published=True)
        return qs

    def perform_create(self, serializer):
        article = serializer.save(author=self.request.user)
        if article.published and not article.published_at:
            article.published_at = timezone.now()
            article.save()
