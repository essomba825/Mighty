from django.contrib import admin

from .models import Payment, PaymentRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'provider', 'amount', 'phone_number', 'status', 'created_at')
    list_filter = ('status', 'provider')
    search_fields = ('reference', 'phone_number')
    readonly_fields = ('reference', 'provider_response', 'created_at', 'updated_at')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('payment_ref', 'project', 'user', 'amount', 'provider',
                    'status', 'created_at')
    list_filter = ('status', 'provider')
    search_fields = ('payment_ref', 'phone_number', 'transaction_code')
    readonly_fields = ('payment_ref', 'created_at', 'verified_at')