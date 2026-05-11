from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, MessageViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'notifications', NotificationViewSet, basename='notification')

conversation_message_list = MessageViewSet.as_view({'get': 'list', 'post': 'create'})
conversation_message_detail = MessageViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

urlpatterns = router.urls + [
    path('conversations/<uuid:conversation_pk>/messages/', conversation_message_list, name='conversation-messages'),
    path('conversations/<uuid:conversation_pk>/messages/<uuid:pk>/', conversation_message_detail, name='conversation-message-detail'),
]
