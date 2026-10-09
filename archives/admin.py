from django.contrib import admin

from .models import ArchiveDocument


@admin.register(ArchiveDocument)
class ArchiveDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'year', 'is_public', 'created_at')
    list_filter = ('doc_type', 'is_public', 'year')
    search_fields = ('title', 'description')
