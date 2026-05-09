from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Event, EventRegistration
from .serializers import EventSerializer, EventRegistrationSerializer
from audit.models import AuditLog

from rest_framework.exceptions import PermissionDenied

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Isolation: students see published events, admins/managers see all (draft/cancelled) of their clubs
        user = self.request.user
        if user.is_administrator:
            return Event.objects.all()
        
        # Base: everyone sees published events
        qs = Event.objects.filter(status='published')
        
        # Managers also see their own club's drafts/cancelled
        if user.role == 'club_manager':
            my_club_ids = user.memberships.filter(
                internal_role__in=['president', 'vice_president'],
                status='approved'
            ).values_list('club_id', flat=True)
            manager_qs = Event.objects.filter(club_id__in=my_club_ids)
            qs = (qs | manager_qs).distinct()
            
        return qs

    def perform_create(self, serializer):
        club = serializer.validated_data['club']
        # Check if user has right to create for this club
        if not self.request.user.is_administrator:
            is_manager = club.memberships.filter(
                user=self.request.user,
                internal_role__in=['president', 'vice_president'],
                status='approved'
            ).exists()
            if not is_manager:
                raise PermissionDenied("You cannot create events for this club.")
        
        event = serializer.save(organizer=self.request.user)
        AuditLog.objects.create(
            user=self.request.user,
            action=AuditLog.ActionType.CREATE,
            resource_type='Event',
            resource_id=event.id,
            detail=f"Created event {event.title}"
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if self.action in ['update', 'partial_update', 'destroy']:
            if not request.user.is_administrator:
                is_manager = obj.club.memberships.filter(
                    user=request.user,
                    internal_role__in=['president', 'vice_president'],
                    status='approved'
                ).exists()
                if not is_manager:
                    self.permission_denied(request, message="You do not have permission to manage this event.")

    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        event = self.get_object()
        
        if event.status != 'published':
            return Response({'error': 'Event is not published'}, status=status.HTTP_400_BAD_REQUEST)
        
        if event.is_full:
            return Response({'error': 'Event is full'}, status=status.HTTP_400_BAD_REQUEST)

        registration, created = EventRegistration.objects.get_or_create(
            user=request.user,
            event=event
        )
        if created:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.REGISTER_EVENT,
                resource_type='Event',
                resource_id=event.id,
                detail=f"Registered for event {event.title}"
            )
            return Response({'status': 'Successfully registered'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'Already registered'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel_registration(self, request, pk=None):
        event = self.get_object()
        registration = EventRegistration.objects.filter(user=request.user, event=event).first()
        
        if registration:
            registration.delete()
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.CANCEL_REGISTRATION,
                resource_type='Event',
                resource_id=event.id,
                detail=f"Cancelled registration for event {event.title}"
            )
            return Response({'status': 'Registration cancelled'}, status=status.HTTP_200_OK)
        return Response({'status': 'Not registered'}, status=status.HTTP_400_BAD_REQUEST)


class EventRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    To list participants. Only visible to admins and club managers.
    """
    queryset = EventRegistration.objects.all()
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_administrator:
            return EventRegistration.objects.all()
        
        # Managers see registrations for their clubs
        if user.role == 'club_manager':
            my_club_ids = user.memberships.filter(
                internal_role__in=['president', 'vice_president'],
                status='approved'
            ).values_list('club_id', flat=True)
            return EventRegistration.objects.filter(event__club_id__in=my_club_ids)
        
        # Students see their own registrations
        return EventRegistration.objects.filter(user=user)
