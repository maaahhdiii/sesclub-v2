import re
import secrets

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404
from users.permissions import IsVerified
from users.models import ClubPortalCredential, Role
from .models import Club, ClubMembership
from .serializers import ClubSerializer, ClubMembershipSerializer
from events.models import Review
from events.serializers import ReviewSerializer
from utils.notify import notify
from utils.audit import log_action


User = get_user_model()


class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]
    search_fields = ['name', 'description']
    filterset_fields = ['is_active']

    def _ensure_admin_for_write(self):
        if self.request.method in permissions.SAFE_METHODS:
            return
        if not getattr(self.request.user, 'is_administrator', False):
            raise PermissionDenied('Only administrators can manage clubs.')

    def perform_create(self, serializer):
        self._ensure_admin_for_write()
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_admin_for_write()
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_admin_for_write()
        instance.delete()

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        club = self.get_object()
        membership, created = ClubMembership.objects.get_or_create(
            club=club,
            user=request.user,
            defaults={'status': 'approved'},
        )
        if membership.status == 'banned':
            return Response({'error': 'You are banned from this club.'}, status=status.HTTP_403_FORBIDDEN)
        if created:
            notify(request.user, 'Club Joined', f'You have joined {club.name}.')
            log_action(request.user, 'MEMBER JOINED', entity_type='Club', entity_id=club.club_id)
        return Response(ClubMembershipSerializer(membership).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def leave(self, request, pk=None):
        club = self.get_object()
        deleted, _ = ClubMembership.objects.filter(club=club, user=request.user).delete()
        if not deleted:
            return Response({'status': 'not a member'}, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ClubMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ClubMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        user = self.request.user
        queryset = ClubMembership.objects.select_related('user', 'club')
        if getattr(user, 'is_administrator', False):
            return queryset
        managed_club_ids = user.club_memberships.filter(
            internal_role__in=['president', 'vice_president'],
            status__in=['active', 'approved'],
        ).values_list('club_id', flat=True)
        if getattr(user, 'is_club_manager', False):
            return queryset.filter(club_id__in=managed_club_ids)
        return queryset.filter(user=user)

    def _send_member_welcome_email(self, target_user, club):
        portal_url = f"{getattr(settings, 'CLUB_PORTAL_URL', 'http://127.0.0.1:8000/club/')}?club_id={club.club_id}"
        from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        subject = f'Welcome to {club.name}'
        text = (
            f'Hello {target_user.first_name or "Student"},\n\n'
            f'Congratulations! You were added to the club "{club.name}".\n\n'
            f'Club portal URL: {portal_url}\n\n'
            'Use Google sign-in with your SESAME account to access this club.\n\n'
            'SESame Clubs Team'
        )
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px;">
            <h2 style="margin:0 0 10px;color:#1f2937;">Welcome to {club.name}</h2>
            <p style="color:#374151;">Congratulations! You were added as a member.</p>
            <p style="color:#374151;">Portal URL: <a href="{portal_url}">{portal_url}</a></p>
            <p style="color:#374151;">Use Google sign-in with your SESAME account (no password login needed for members).</p>
        </div>
        """
        message = EmailMultiAlternatives(subject, text, from_email, [target_user.email])
        message.attach_alternative(html, 'text/html')
        message.send(fail_silently=False)

    def _generate_temp_password(self, length=12):
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _build_club_manager_username(self, club):
        slug = re.sub(r'[^a-z0-9]+', '-', (club.name or '').strip().lower()).strip('-') or 'club'
        base = f'{slug[:40]}-{str(club.club_id)[:8]}@clubs.sesame.com.tn'
        candidate = base
        counter = 1
        while ClubPortalCredential.objects.filter(username__iexact=candidate).exists() or User.objects.filter(username__iexact=candidate).exists():
            candidate = f'{slug[:32]}-{counter}-{str(club.club_id)[:8]}@clubs.sesame.com.tn'
            counter += 1
        return candidate

    def _send_club_manager_email(self, target_user, club, username, temp_password):
        portal_url = f"{getattr(settings, 'CLUB_PORTAL_URL', 'http://127.0.0.1:8000/club/')}?club_id={club.club_id}"
        from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        subject = f'Your Club Manager Access for {club.name}'
        text = (
            f'Hello {target_user.first_name or "Manager"},\n\n'
            f'Your manager access for "{club.name}" is ready.\n\n'
            f'Portal URL: {portal_url}\n'
            f'Username: {username}\n'
            f'Password: {temp_password}\n\n'
            'Use these credentials only for this club portal.\n'
            'SESame Clubs Team'
        )
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px;">
            <h2 style="margin:0 0 10px;color:#1f2937;">Club Manager Access Ready</h2>
            <p style="color:#374151;">Your club <strong>{club.name}</strong> manager access is ready.</p>
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px;">
                <p style="margin:6px 0;"><strong>Portal URL:</strong> <a href="{portal_url}">{portal_url}</a></p>
                <p style="margin:6px 0;"><strong>Username:</strong> {username}</p>
                <p style="margin:6px 0;"><strong>Password:</strong> {temp_password}</p>
            </div>
            <p style="margin-top:14px;color:#374151;">These credentials are specific to this club only.</p>
        </div>
        """
        message = EmailMultiAlternatives(subject, text, from_email, [target_user.email])
        message.attach_alternative(html, 'text/html')
        message.send(fail_silently=False)

    def perform_create(self, serializer):
        user = self.request.user
        club = serializer.validated_data['club']
        target_user = serializer.validated_data['user']
        if getattr(user, 'is_administrator', False):
            membership = serializer.save(status='approved')
            if membership.internal_role in ['president', 'vice_president']:
                if target_user.role != Role.ADMIN:
                    target_user.role = Role.CLUB_MANAGER
                    target_user.save(update_fields=['role'])
                username = self._build_club_manager_username(club)
                temp_password = self._generate_temp_password()
                credential = ClubPortalCredential(user=target_user, club=club, username=username, is_active=True)
                credential.set_password(temp_password)
                credential.save()
                notify(target_user, 'Club Manager Access', f'You are now managing {club.name}.')
                try:
                    self._send_club_manager_email(target_user, club, username, temp_password)
                except Exception:
                    pass
            else:
                notify(target_user, 'Club Membership', f'You were added to {club.name}.')
                try:
                    self._send_member_welcome_email(target_user, club)
                except Exception:
                    pass
            return
        is_manager = user.club_memberships.filter(
            club=club,
            internal_role__in=['president', 'vice_president'],
            status__in=['active', 'approved'],
        ).exists()
        if not is_manager:
            raise PermissionDenied('Only club presidents can add members.')
        if target_user.is_administrator:
            raise PermissionDenied('Administrator accounts cannot be added to a club by a president.')
        membership = serializer.save(status='approved')
        notify(target_user, 'Club Membership', f'You were added to {club.name}.')
        try:
            self._send_member_welcome_email(target_user, club)
        except Exception:
            pass
        log_action(user, 'MEMBER JOINED', entity_type='ClubMembership', entity_id=None, metadata={'club': str(club.club_id), 'member': str(target_user.id)})

    def perform_destroy(self, instance):
        user = self.request.user
        if getattr(user, 'is_administrator', False) or instance.user_id == user.id:
            instance.delete()
            return
        is_manager = user.club_memberships.filter(
            club=instance.club,
            internal_role__in=['president', 'vice_president'],
            status__in=['active', 'approved'],
        ).exists()
        if not is_manager:
            raise PermissionDenied('You do not have permission to manage this membership.')
        log_action(user, 'MEMBER KICKED', entity_type='ClubMembership', entity_id=instance.id, metadata={'club': str(instance.club_id)})
        instance.delete()


class ClubReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        club = get_object_or_404(Club, pk=self.kwargs['club_pk'])
        return Review.objects.filter(club=club).select_related('user')

    def perform_create(self, serializer):
        club = get_object_or_404(Club, pk=self.kwargs['club_pk'])
        if getattr(self.request.user, 'is_administrator', False):
            serializer.save(user=self.request.user, club=club)
            return
        is_member = ClubMembership.objects.filter(
            user=self.request.user,
            club=club,
            status__in=['active', 'approved'],
        ).exists()
        if not is_member:
            raise PermissionDenied('You must be a member to review this club.')
        if Review.objects.filter(user=self.request.user, club=club).exists():
            raise ValidationError({'error': 'You have already reviewed this club.'})
        review = serializer.save(user=self.request.user, club=club)
        notify(self.request.user, 'Review Saved', f'Your review for {club.name} was saved.')
        log_action(self.request.user, 'ROLE CHANGED', entity_type='Review', entity_id=review.id, metadata={'club': str(club.club_id)})
