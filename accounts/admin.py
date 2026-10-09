from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, ActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'role', 'status', 'is_staff', 'is_superuser']
    list_filter = ['role', 'status', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['email']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations Métier', {'fields': ('role', 'status', 'phone')}),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Journal en lecture seule.

    Une trace que l'on peut modifier ne prouve rien. Les lignes se remplissent
    par le code, jamais a la main.
    """

    list_display = ['created_at', 'actor_label', 'action', 'model_name',
                    'summary', 'ip_address']
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['actor_label', 'summary', 'object_id', 'model_name']
    date_hierarchy = 'created_at'
    readonly_fields = [f.name for f in ActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # La purge reste possible, mais seulement pour un admin, et c'est un
        # choix delibere : une base qui grossit sans fin finira par Bloom.
        return request.user.is_superuser