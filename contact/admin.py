from django.contrib import admin

from .models import ContactInfo, ContactMessage


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone')
    def has_add_permission(self, request):
        return not ContactInfo.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('name', 'email', 'subject', 'message')
    actions = ['mark_read']

    @admin.action(description='Marquer comme lu')
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)