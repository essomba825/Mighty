from rest_framework import permissions, viewsets

from .models import ArchiveDocument
from .serializers import ArchiveDocumentSerializer


class ArchiveDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = ArchiveDocumentSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = ArchiveDocument.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_public=True)
        doc_type = self.request.query_params.get('type')
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
