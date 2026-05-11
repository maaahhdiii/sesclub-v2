from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Conversation, Message, Notification

User = get_user_model()


class ConversationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='conversation_id', read_only=True)
    participants = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, required=False)

    class Meta:
        model = Conversation
        fields = ('id', 'created_at', 'participants')
        read_only_fields = ('id', 'created_at')


class MessageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='message_id', read_only=True)
    conversation = serializers.PrimaryKeyRelatedField(queryset=Conversation.objects.all(), required=False)

    class Meta:
        model = Message
        fields = ('id', 'body', 'is_read', 'conversation', 'sender')
        read_only_fields = ('id', 'sender')


class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='notification_id', read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'title', 'body', 'is_read', 'created_at', 'user')
        read_only_fields = ('id', 'created_at', 'user')
