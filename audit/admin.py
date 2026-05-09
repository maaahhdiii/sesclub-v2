from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'entity_type', 'entity_id', 'ip_adress')
    list_filter = ('action', 'entity_type')
    readonly_fields = ('log_id', 'timestamp', 'user', 'action', 'entity_type', 'entity_id', 'ip_adress', 'metadata')
