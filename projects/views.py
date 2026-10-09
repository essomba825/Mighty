from rest_framework import permissions, viewsets

from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Project.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.exclude(status='draft')
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
