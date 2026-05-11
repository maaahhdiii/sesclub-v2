from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from users.permissions import IsVerified
from clubs.models import ClubMembership
from utils.notify import notify
from utils.audit import log_action

from .models import Event, EventRegistration, Review
from .serializers import EventSerializer, EventRegistrationSerializer, ReviewSerializer
from django.conf import settings
from django.utils import timezone
import requests
from rest_framework.views import APIView


class GoogleAuthUrlView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get(self, request):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT', None)
        if not client_id or not redirect_uri:
            return Response({'error': 'Google OAuth not configured on server.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

        params = {
            'client_id': client_id,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.email',
            'redirect_uri': redirect_uri,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + requests.utils.requote_uri('&'.join([f"{k}={requests.utils.requote_uri(v)}" for k, v in params.items()]))
        return Response({'auth_url': auth_url})


class GoogleCallbackView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({'error': 'Missing code'}, status=status.HTTP_400_BAD_REQUEST)

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT', None)
        if not client_id or not client_secret or not redirect_uri:
            return Response({'error': 'Google OAuth not configured on server.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

        token_endpoint = 'https://oauth2.googleapis.com/token'
        data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        try:
            r = requests.post(token_endpoint, data=data, timeout=10)
            r.raise_for_status()
            token_data = r.json()
        except Exception as exc:
            return Response({'error': 'Token exchange failed', 'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        from .models import GoogleCalendarCredentials
        creds, _ = GoogleCalendarCredentials.objects.get_or_create(user=request.user)
        creds.access_token = token_data.get('access_token')
        creds.refresh_token = token_data.get('refresh_token') or creds.refresh_token
        creds.token_type = token_data.get('token_type')
        expires_in = token_data.get('expires_in')
        if expires_in:
            creds.expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
        creds.save()

        return Response({'status': 'connected'})


class SyncEventToGoogleView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def post(self, request, pk=None):
        """Sync a single event (pk) to user's Google Calendar if connected."""
        from .models import GoogleCalendarCredentials
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            creds = GoogleCalendarCredentials.objects.get(user=request.user)
        except GoogleCalendarCredentials.DoesNotExist:
            return Response({'error': 'No Google calendar connected'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to post event to Google Calendar v3
        api_url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
        headers = {'Authorization': f'Bearer {creds.access_token}', 'Content-Type': 'application/json'}
        body = {
            'summary': event.title,
            'description': event.description,
            'location': event.location,
            'start': {'dateTime': event.date.isoformat()},
            'end': {'dateTime': (event.date + timezone.timedelta(hours=2)).isoformat()},
        }
        try:
            r = requests.post(api_url, json=body, headers=headers, timeout=10)
            if r.status_code == 401 and creds.refresh_token:
                # Try refresh
                token_endpoint = 'https://oauth2.googleapis.com/token'
                data = {'client_id': settings.GOOGLE_CLIENT_ID, 'client_secret': settings.GOOGLE_CLIENT_SECRET, 'refresh_token': creds.refresh_token, 'grant_type': 'refresh_token'}
                tr = requests.post(token_endpoint, data=data, timeout=10); tr.raise_for_status(); td = tr.json()
                creds.access_token = td.get('access_token');
                expires_in = td.get('expires_in');
                if expires_in: creds.expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
                creds.save()
                headers['Authorization'] = f'Bearer {creds.access_token}'
                r = requests.post(api_url, json=body, headers=headers, timeout=10)

            r.raise_for_status()
        except Exception as exc:
            return Response({'error': 'Failed to sync to Google', 'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'synced', 'google_event': r.json()})

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    search_fields = ['title', 'description', 'location', 'club__name']
    filterset_fields = ['status', 'club']

    def get_queryset(self):
        return Event.objects.all()

    def perform_create(self, serializer):
        club = serializer.validated_data['club']
        if not getattr(self.request.user, 'is_administrator', False):
            is_manager = club.memberships.filter(
                user=self.request.user,
                internal_role__in=['president', 'vice_president'],
                status__in=['active', 'approved'],
            ).exists()
            if not is_manager:
                raise PermissionDenied('You cannot create events for this club.')
        serializer.save(organizer=self.request.user)

    def perform_update(self, serializer):
        event = self.get_object()
        if not getattr(self.request.user, 'is_administrator', False):
            is_manager = event.club.memberships.filter(
                user=self.request.user,
                internal_role__in=['president', 'vice_president'],
                status__in=['active', 'approved'],
            ).exists()
            if not is_manager:
                raise PermissionDenied('You do not have permission to manage this event.')
        serializer.save()

    def perform_destroy(self, instance):
        if not getattr(self.request.user, 'is_administrator', False):
            is_manager = instance.club.memberships.filter(
                user=self.request.user,
                internal_role__in=['president', 'vice_president'],
                status__in=['active', 'approved'],
            ).exists()
            if not is_manager:
                raise PermissionDenied('You do not have permission to manage this event.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        event = self.get_object()
        if event.status == 'cancelled':
            return Response({'error': 'Event is not available'}, status=status.HTTP_400_BAD_REQUEST)
        if event.capacity > 0 and event.registrations.count() >= event.capacity:
            return Response({'error': 'Event is full'}, status=status.HTTP_400_BAD_REQUEST)

        _, created = EventRegistration.objects.get_or_create(user=request.user, event=event)
        if not created:
            return Response({'status': 'Already registered'}, status=status.HTTP_400_BAD_REQUEST)
        notify(request.user, 'Event Registration', f'You are registered for {event.title}.')
        log_action(request.user, 'ROLE CHANGED', entity_type='Event', entity_id=event.id, metadata={'action': 'register'})
        return Response({'status': 'registered'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def unregister(self, request, pk=None):
        event = self.get_object()
        EventRegistration.objects.filter(user=request.user, event=event).delete()
        return Response({'status': 'unregistered'})


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        event = get_object_or_404(Event, pk=self.kwargs['event_pk'])
        if getattr(self.request.user, 'is_administrator', False):
            return Review.objects.filter(event=event)
        return Review.objects.filter(event=event, user=self.request.user)

    def perform_create(self, serializer):
        event = get_object_or_404(Event, pk=self.kwargs['event_pk'])
        if getattr(self.request.user, 'is_administrator', False):
            serializer.save(user=self.request.user, event=event)
            return
        if not event.club:
            raise PermissionDenied('This event cannot be reviewed yet.')
        is_member = ClubMembership.objects.filter(
            user=self.request.user,
            club=event.club,
            status__in=['active', 'approved'],
        ).exists()
        if not is_member:
            raise PermissionDenied('You must be a member to review this event.')
        review = serializer.save(user=self.request.user, event=event)
        notify(self.request.user, 'Review Saved', f'Your review for {event.title} was saved.')
        log_action(self.request.user, 'ROLE CHANGED', entity_type='Review', entity_id=review.id, metadata={'event': str(event.id)})


class EventRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    To list participants. Only visible to admins and club managers.
    """
    queryset = EventRegistration.objects.all()
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'is_administrator', False):
            return EventRegistration.objects.all()
        if getattr(user, 'is_club_manager', False):
            my_club_ids = user.club_memberships.filter(
                internal_role__in=['president', 'vice_president'],
                status__in=['active', 'approved'],
            ).values_list('club_id', flat=True)
            return EventRegistration.objects.filter(event__club_id__in=my_club_ids)
        return EventRegistration.objects.filter(user=user)
