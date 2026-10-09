from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'budget', 'amount_collected', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'objective')
