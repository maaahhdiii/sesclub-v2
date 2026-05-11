from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, EventRegistrationViewSet, ReviewViewSet
from .views import GoogleAuthUrlView, GoogleCallbackView, SyncEventToGoogleView

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'registrations', EventRegistrationViewSet, basename='registration')

review_list = ReviewViewSet.as_view({'get': 'list', 'post': 'create'})
review_detail = ReviewViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'})

urlpatterns = [
    path('', include(router.urls)),
    path('events/google/auth-url/', GoogleAuthUrlView.as_view(), name='google-auth-url'),
    path('events/google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
    path('events/<int:pk>/sync_google/', SyncEventToGoogleView.as_view(), name='sync-event-google'),
    path('events/<int:event_pk>/reviews/', review_list, name='event-reviews'),
    path('events/<int:event_pk>/reviews/<int:pk>/', review_detail, name='event-review-detail'),
]
