from django.contrib import admin

from .models import MentorshipOffer, MentorshipRequest


@admin.register(MentorshipOffer)
class MentorshipOfferAdmin(admin.ModelAdmin):
    list_display = ('field', 'mentor', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('field', 'mentor__first_name', 'mentor__last_name')


@admin.register(MentorshipRequest)
class MentorshipRequestAdmin(admin.ModelAdmin):
    list_display = ('offer', 'mentee', 'status', 'created_at')
    list_filter = ('status',)
