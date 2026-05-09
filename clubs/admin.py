from django.contrib import admin
from .models import Club, ClubMembership

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')

@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'club', 'joined_at')
