from django.contrib import admin

from .models import Contribution, PartnershipRequest


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'amount', 'method', 'project', 'status', 'created_at')
    list_filter = ('status', 'method', 'project')
    search_fields = ('donor_name', 'donor_email')
    actions = ['mark_confirmed', 'mark_rejected']

    @admin.action(description='Confirmer les contributions sélectionnées')
    def mark_confirmed(self, request, queryset):
        queryset.update(status='confirmed')

    @admin.action(description='Rejeter les contributions sélectionnées')
    def mark_rejected(self, request, queryset):
        queryset.update(status='rejected')


@admin.register(PartnershipRequest)
class PartnershipRequestAdmin(admin.ModelAdmin):
    list_display = ('organization', 'contact_name', 'partner_type', 'status', 'created_at')
    list_filter = ('status', 'partner_type')
    search_fields = ('organization', 'contact_name', 'email')
    actions = ['mark_contacted', 'mark_accepted', 'mark_refused']

    @admin.action(description='Passer en cours de traitement')
    def mark_contacted(self, request, queryset):
        queryset.update(status='contacted')

    @admin.action(description='Accepter les demandes sélectionnées')
    def mark_accepted(self, request, queryset):
        queryset.update(status='accepted')

    @admin.action(description='Refuser les demandes sélectionnées')
    def mark_refused(self, request, queryset):
        queryset.update(status='refused')
