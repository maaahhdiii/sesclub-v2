from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='log_id', read_only=True)
    ip = serializers.CharField(source='ip_adress', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = ('id', 'action', 'metadata', 'ip', 'ip_adress', 'timestamp', 'entity_type', 'entity_id', 'user', 'user_email')
        read_only_fields = fields
