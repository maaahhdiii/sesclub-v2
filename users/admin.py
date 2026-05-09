from django.contrib import admin
from .models import User, Role, Privelege

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'created_at')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Privelege)
class PrivelegeAdmin(admin.ModelAdmin):
    list_display = ('action',)
