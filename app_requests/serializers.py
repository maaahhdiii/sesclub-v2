from rest_framework import serializers
from .models import Request
from users.serializers import UserSerializer


class RequestSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='request_id', read_only=True)
    request_type = serializers.CharField()
    user = UserSerializer(read_only=True)
    treated_by = UserSerializer(read_only=True)

    class Meta:
        model = Request
        fields = ('id', 'request_type', 'status', 'title', 'description', 'metadata', 'created_at', 'user', 'treated_by')
        read_only_fields = ('id', 'created_at', 'user', 'treated_by')

    def validate_request_type(self, value):
        normalized = (value or '').replace('_', ' ').upper()
        valid_values = {choice for choice, _ in Request.RequestType.choices}
        if normalized not in valid_values:
            raise serializers.ValidationError('Invalid request type.')
        return normalized

    def validate(self, attrs):
        return super().validate(attrs)
