from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('title', 'message', 'user__email')


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'last_seen')
    search_fields = ('user__email', 'endpoint')
    readonly_fields = ('user', 'endpoint', 'p256dh', 'auth', 'created_at', 'last_seen')
