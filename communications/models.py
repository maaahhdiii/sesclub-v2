import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Represents a Notification matching the 'Notification' class in the class diagram.
    """
    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 1* Recevoir relation
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return self.title


class Conversation(models.Model):
    """
    Represents a Conversation matching the 'Conversation' class in the class diagram.
    """
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 1..* Participer relation
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'

    def __str__(self):
        return f"Conversation {self.conversation_id}"


class Message(models.Model):
    """
    Represents a Message matching the 'Message' class in the class diagram.
    """
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    body = models.TextField(blank=True, default='')
    is_read = models.BooleanField(default=False)
    
    # Relationships implicitly derived from context (messages belong to conversation, sent by a user)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"Message from {self.sender.username}"
