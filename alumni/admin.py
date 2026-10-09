from django.contrib import admin

from .cards import issue_card
from .models import AlumniProfile, MemberCard


@admin.register(AlumniProfile)
class AlumniProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'graduation_year', 'profession', 'city', 'card_number',
                    'is_visible_in_directory')
    list_filter = ('graduation_year', 'is_visible_in_directory')
    search_fields = ('user__first_name', 'user__last_name', 'profession', 'city')
    actions = ['issue_cards']

    @admin.display(description="N° de carte")
    def card_number(self, obj):
        card = getattr(obj, 'member_card', None)
        return card.card_number if card else '—'

    @admin.action(description="Générer / renouveler les cartes sélectionnées")
    def issue_cards(self, request, queryset):
        created = 0
        for profile in queryset:
            card = issue_card(profile, signed_by=request.user.get_full_name())
            created += 1
        self.message_user(request, f'{created} carte(s) générée(s) / renouvelée(s).')


@admin.register(MemberCard)
class MemberCardAdmin(admin.ModelAdmin):
    list_display = ('card_number', 'profile', 'valid_until', 'is_active', 'signed_by', 'issued_at')
    list_filter = ('is_active',)
    search_fields = ('card_number', 'profile__user__first_name', 'profile__user__last_name')
