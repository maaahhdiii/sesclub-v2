from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from users.permissions import IsVerified

from .models import Conversation, Message, Notification
from .serializers import ConversationSerializer, MessageSerializer, NotificationSerializer


class ConversationViewSet(viewsets.ModelViewSet):
	serializer_class = ConversationSerializer
	permission_classes = [permissions.IsAuthenticated, IsVerified]

	def get_queryset(self):
		return self.request.user.conversations.all()

	def perform_create(self, serializer):
		participants = list(serializer.validated_data.pop('participants', []))
		conversation = serializer.save()
		conversation.participants.add(self.request.user, *participants)


class MessageViewSet(viewsets.ModelViewSet):
	serializer_class = MessageSerializer
	permission_classes = [permissions.IsAuthenticated, IsVerified]

	def get_queryset(self):
		conversation_pk = self.kwargs.get('conversation_pk')
		if conversation_pk:
			return Message.objects.filter(conversation_id=conversation_pk).order_by('message_id')
		return Message.objects.filter(conversation__participants=self.request.user).order_by('message_id')

	def perform_create(self, serializer):
		conversation_pk = self.kwargs.get('conversation_pk')
		if conversation_pk:
			serializer.save(sender=self.request.user, conversation_id=conversation_pk)
			return
		serializer.save(sender=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
	serializer_class = NotificationSerializer
	permission_classes = [permissions.IsAuthenticated, IsVerified]

	def get_queryset(self):
		user = self.request.user
		if getattr(user, 'is_administrator', False):
			return Notification.objects.all()
		return Notification.objects.filter(user=user)

	@action(detail=True, methods=['patch'])
	def read(self, request, pk=None):
		notification = self.get_object()
		notification.is_read = True
		notification.save(update_fields=['is_read'])
		return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)
