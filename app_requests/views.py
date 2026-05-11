import secrets
import string
import re

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from clubs.models import Club, ClubMembership
from users.models import ClubPortalCredential, Role
from users.permissions import IsVerified
from utils.audit import log_action
from utils.notify import notify

from .models import Request
from .serializers import RequestSerializer


User = get_user_model()


class RequestViewSet(viewsets.ModelViewSet):
    serializer_class = RequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == Role.ADMIN or getattr(user, 'is_administrator', False):
            return Request.objects.all()
        return Request.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _generate_temp_password(self, length=12):
        # Avoid ambiguous characters and punctuation that are easy to mistype from email.
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _build_portal_username(self, user):
        email_candidate = (getattr(user, 'email', '') or '').strip().lower()
        if '@' in email_candidate:
            return email_candidate

        username_candidate = (getattr(user, 'username', '') or '').strip().lower()
        if '@' in username_candidate:
            return username_candidate
        if username_candidate:
            return f'{username_candidate}@sesame.com.tn'
        return f'user-{user.id}@sesame.com.tn'

    def _build_club_manager_username(self, club):
        slug = re.sub(r'[^a-z0-9]+', '-', (club.name or '').strip().lower()).strip('-') or 'club'
        base = f'{slug[:40]}-{str(club.club_id)[:8]}@clubs.sesame.com.tn'
        candidate = base
        counter = 1
        while ClubPortalCredential.objects.filter(username__iexact=candidate).exists() or User.objects.filter(username__iexact=candidate).exists():
            candidate = f'{slug[:32]}-{counter}-{str(club.club_id)[:8]}@clubs.sesame.com.tn'
            counter += 1
        return candidate

    def _send_club_portal_credentials(self, user, club, username, temp_password):
        club_portal_url = getattr(settings, 'CLUB_PORTAL_URL', 'http://127.0.0.1:8000/club/')
        club_specific_url = f'{club_portal_url}?club_id={club.club_id}'
        from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        subject = 'Your Club Portal Credentials'
        text = (
            f'Hello {user.first_name or "Student"},\n\n'
            f'Your club request for "{club.name}" has been approved.\n\n'
            'Use these credentials to access this specific club portal:\n'
            f'Portal URL: {club_specific_url}\n'
            f'Username: {username}\n'
            f'Password: {temp_password}\n\n'
            'These manager credentials are tied to this club request.\n'
            'Club members should use Google sign-in with their own SESAME account.\n\n'
            'SESame Clubs Team'
        )
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px;">
            <h2 style="margin:0 0 10px;color:#1f2937;">Club Request Approved</h2>
            <p style="color:#374151;">Your club <strong>{club.name}</strong> is now approved.</p>
            <p style="color:#374151;">Use these credentials to access this specific club portal:</p>
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px;">
                <p style="margin:6px 0;"><strong>Portal URL:</strong> <a href="{club_specific_url}">{club_specific_url}</a></p>
                <p style="margin:6px 0;"><strong>Username:</strong> {username}</p>
                <p style="margin:6px 0;"><strong>Password:</strong> {temp_password}</p>
            </div>
            <p style="margin-top:14px;color:#374151;">These manager credentials are specific to this club.</p>
            <p style="margin-top:14px;color:#374151;">Club members should use Google sign-in with their own SESAME account.</p>
        </div>
        """
        message = EmailMultiAlternatives(
            subject,
            text,
            from_email,
            [user.email],
        )
        message.attach_alternative(html, 'text/html')
        message.send(fail_silently=False)

    def _handle_club_creation_approval(self, req):
        if req.request_type != Request.RequestType.CLUB_CREATION:
            return
        if req.status != Request.RequestStatus.TREATED:
            return
        if (req.metadata or {}).get('created_club_id'):
            return

        requester = req.user
        if requester is None:
            return

        metadata = req.metadata or {}
        club_name = metadata.get('club_name') or req.title
        club_description = metadata.get('club_description') or req.description
        club_category = metadata.get('club_category') or ''

        if Club.objects.filter(name=club_name).exists():
            raise PermissionDenied('A club with this name already exists.')

        club = Club.objects.create(
            name=club_name,
            description=club_description,
            category=club_category,
            is_active=True,
        )

        username = self._build_club_manager_username(club)
        temp_password = self._generate_temp_password()
        requester.role = Role.CLUB_MANAGER
        requester.save(update_fields=['role'])

        credential = ClubPortalCredential(
            user=requester,
            club=club,
            username=username,
            is_active=True,
        )
        credential.set_password(temp_password)
        credential.save()

        ClubMembership.objects.update_or_create(
            user=requester,
            club=club,
            defaults={'internal_role': 'president', 'status': 'approved'},
        )

        req.metadata = {
            **metadata,
            'created_club_id': str(club.club_id),
            'president_user_id': str(requester.id),
            'club_portal_username': username,
            'club_portal_url': f"{getattr(settings, 'CLUB_PORTAL_URL', 'http://127.0.0.1:8000/club/')}?club_id={club.club_id}",
            'credentials_sent': True,
        }
        req.save(update_fields=['metadata'])

        self._send_club_portal_credentials(requester, club, username, temp_password)
        notify(requester, 'Club request approved', f'Your club "{club.name}" is ready and you are now its president.')

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        if getattr(request.user, 'role', None) != Role.ADMIN and not getattr(request.user, 'is_administrator', False):
            raise PermissionDenied()

        req = self.get_object()
        raw_status = request.data.get('status')
        if isinstance(raw_status, str):
            req.status = raw_status.replace('_', ' ').upper()
        req.treated_by = request.user
        req.save()

        self._handle_club_creation_approval(req)

        if req.user:
            notify(req.user, 'Request Updated', f'Your request "{req.title}" is now {req.status}.')
        log_action(
            request.user,
            'ROLE ASSIGNED',
            entity_type='Request',
            entity_id=req.request_id,
            metadata={'status': req.status},
        )
        return Response(RequestSerializer(req).data, status=status.HTTP_200_OK)
