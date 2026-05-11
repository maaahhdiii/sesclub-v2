from rest_framework import generics, permissions, viewsets
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs
import json
from social_django.views import complete as social_complete
from social_core.exceptions import AuthException

from .serializers import UserSerializer, UserRegistrationSerializer, CustomTokenObtainPairSerializer
from .models import EmailVerificationCode, Role
from .permissions import IsVerified
from utils.audit import log_action
from clubs.models import ClubMembership

User = get_user_model()


def send_verification_email(user, code):
    subject = 'Your SESame verification code'
    text = f'Your code is: {code}\nValid for 10 minutes.'
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:32px;border:1px solid #eee;border-radius:8px;">
        <h2 style="color:#1a1a2e;">Welcome to SESame Clubs 🎓</h2>
        <p>Your email verification code is:</p>
        <div style="font-size:40px;font-weight:bold;letter-spacing:12px;color:#e94560;text-align:center;padding:16px 0;">{code}</div>
        <p style="color:#888;font-size:13px;">Valid for 10 minutes. If you did not request this, ignore this email.</p>
    </div>
    """
    message = EmailMultiAlternatives(subject, text, None, [user.email])
    message.attach_alternative(html, 'text/html')
    message.send()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class CustomTokenVerifyView(TokenVerifyView):
    permission_classes = [permissions.AllowAny]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        user.is_verified = False
        user.save(update_fields=['is_verified'])

        code = EmailVerificationCode.generate_for(user)
        self._verification_code = code
        send_verification_email(user, code)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data['message'] = 'Registration successful. Check your email for a 6-digit verification code.'
        from django.conf import settings
        if settings.DEBUG and getattr(self, '_verification_code', None):
            response.data['verification_code'] = self._verification_code
        return response


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        data = serializer.data
        
        # Add club membership info for the selected club
        selected_club_id = request.GET.get('club_id') or request.session.get('selected_club_id')
        if selected_club_id:
            from clubs.models import ClubMembership
            try:
                membership = ClubMembership.objects.get(user=user, club_id=selected_club_id)
                data['is_club_member'] = True
                data['club_internal_role'] = membership.internal_role
                data['club_membership_status'] = membership.status
            except ClubMembership.DoesNotExist:
                data['is_club_member'] = False
                data['club_internal_role'] = None
                data['club_membership_status'] = None
        else:
            data['is_club_member'] = False
            data['club_internal_role'] = None
            data['club_membership_status'] = None
        
        return Response(data)

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(user, 'USER PROFILE UPDATED', entity_type='User', entity_id=user.id)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerified]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'is_administrator', False):
            return User.objects.all()
        if getattr(user, 'is_club_manager', False):
            return User.objects.filter(role=Role.STUDENT, is_verified=True)
        return User.objects.filter(id=user.id)


class GoogleCompleteView(APIView):
    permission_classes = []

    def get(self, request, backend=None, *args, **kwargs):
        try:
            return social_complete(request, backend, *args, **kwargs)
        except AuthException as exc:
            reason = quote(str(exc))
            return redirect(f'/api/v1/auth/google/error/?reason={reason}')
        except Exception as exc:
            reason = quote(str(exc))
            return redirect(f'/api/v1/auth/google/error/?reason={reason}')


class GoogleStudentLoginView(APIView):
    permission_classes = []

    def get(self, request):
        request.session['google_portal_target'] = 'student'
        return redirect('/api/v1/auth/google/login/google-oauth2/')


class GoogleClubLoginView(APIView):
    permission_classes = []

    def get(self, request):
        request.session['google_portal_target'] = 'club'
        club_id = request.query_params.get('club_id')
        if not club_id:
            referrer = request.META.get('HTTP_REFERER', '')
            if referrer:
                parsed = urlparse(referrer)
                club_id = (parse_qs(parsed.query).get('club_id') or [None])[0]
        if club_id:
            request.session['google_club_id'] = club_id
        elif request.user.is_authenticated:
            fallback_membership = ClubMembership.objects.filter(
                user=request.user,
                status__in=['active', 'approved'],
            ).order_by('-joined_at').first()
            if fallback_membership:
                request.session['google_club_id'] = str(fallback_membership.club_id)
        return redirect('/api/v1/auth/google/login/google-oauth2/')


class GoogleSuccessView(GoogleCompleteView):
    authentication_classes = [SessionAuthentication]

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return HttpResponse("""
                <!doctype html>
                <html>
                    <head>
                        <meta charset='utf-8'/>
                        <meta name='viewport' content='width=device-width,initial-scale=1'/>
                        <title>Google login not finished</title>
                        <style>
                            body{font-family:Arial,sans-serif;background:#f6fbff;color:#032033;padding:40px;display:flex;justify-content:center}
                            .card{background:white;border-radius:12px;padding:32px;border:1px solid #d6e6f2;max-width:500px;box-shadow:0 4px 6px rgba(0,0,0,0.05)}
                            a{color:#38bdf8;text-decoration:none;font-weight:bold}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h2>Google login not finished yet</h2>
                            <p>Start Google login first, then come back here after Google redirects you back.</p>
                            <p><a href='/api/v1/auth/google/login/google-oauth2/'>Start Google login</a></p>
                        </div>
                    </body>
                </html>
            """)

        forced_target = request.session.pop('google_portal_target', None)

        # Respect explicit login entrypoint intent first, then fallback to role-based routing.
        if forced_target == 'student':
            frontend_url = request.build_absolute_uri('/student/')
            portal_name = 'student portal'
        elif forced_target == 'club':
            club_target_id = request.session.pop('google_club_id', None)
            if not club_target_id:
                fallback_membership = ClubMembership.objects.filter(
                    user=user,
                    status__in=['active', 'approved'],
                ).order_by('-joined_at').first()
                if fallback_membership:
                    club_target_id = str(fallback_membership.club_id)
            if club_target_id:
                club_suffix = f'?club_id={quote(str(club_target_id))}'
                frontend_url = request.build_absolute_uri(f'/club/{club_suffix}')
                portal_name = 'club portal'
            else:
                # Explicit club login requested but no club context resolved —
                # avoid sending a user with no club membership/credentials straight into the club portal.
                frontend_url = request.build_absolute_uri('/student/')
                portal_name = 'student portal'
        elif user.is_administrator:
            frontend_url = request.build_absolute_uri('/admin-page/')
            portal_name = "administrator portal"
        elif user.is_club_manager:
            # Only route to the club portal if the user actually has an active club context.
            # A user may retain the `club_manager` role but no longer manage any club —
            # in that case send them to the student portal instead of granting club access.
            club_target_id = request.session.pop('google_club_id', None)
            if not club_target_id:
                # Prefer explicit manager credentials, then any active membership
                mc = user.club_portal_credentials.filter(is_active=True).first() if hasattr(user, 'club_portal_credentials') else None
                if mc:
                    club_target_id = str(mc.club_id)
                else:
                    fallback_membership = ClubMembership.objects.filter(
                        user=user,
                        status__in=['active', 'approved'],
                    ).order_by('-joined_at').first()
                    if fallback_membership:
                        club_target_id = str(fallback_membership.club_id)

            if club_target_id:
                club_suffix = f'?club_id={quote(str(club_target_id))}'
                frontend_url = request.build_absolute_uri(f'/club/{club_suffix}')
                portal_name = 'club manager portal'
            else:
                frontend_url = request.build_absolute_uri('/student/')
                portal_name = 'student portal'
        else:
            frontend_url = request.build_absolute_uri('/student/')
            portal_name = "student portal"

        refresh = RefreshToken.for_user(user)
        redirect_payload = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_admin': user.is_administrator,
                'is_club_manager': user.is_club_manager,
                'is_verified': user.is_verified,
            },
            'target': frontend_url,
        }

        html = f"""
        <!doctype html>
        <html>
            <head>
                <meta charset='utf-8'/>
                <meta name='viewport' content='width=device-width,initial-scale=1'/>
                <title>Google login successful</title>
                <style>
                    body{{font-family:Arial,Helvetica,sans-serif;background:#f6fbff;color:#032033;padding:24px}}
                    .card{{background:white;border-radius:12px;padding:24px;border:1px solid #d6e6f2;max-width:720px;box-shadow:0 16px 40px rgba(10,30,50,.08)}}
                    a.button{{display:inline-block;padding:10px 14px;background:#38bdf8;color:#02233a;border:0;border-radius:8px;text-decoration:none;cursor:pointer}}
                    .muted{{color:#5b7285}}
                </style>
            </head>
            <body>
                <div class='card'>
                    <h2>Google login successful</h2>
                    <p class='muted'>Signed in as {user.email}. Redirecting you back to the {portal_name}...</p>
                    <p><a class='button' id='continue-link' href='{frontend_url}'>Continue to {portal_name}</a></p>
                </div>
                <script>
                    const payload = {json.dumps(redirect_payload)};
                    const target = new URL(payload.target);
                    target.hash = new URLSearchParams({{
                        access: payload.access,
                        refresh: payload.refresh,
                        user: JSON.stringify(payload.user)
                    }}).toString();
                    document.getElementById('continue-link').href = target.toString();
                    window.location.replace(target.toString());
                </script>
            </body>
        </html>
        """
        return HttpResponse(html)


class GoogleErrorView(APIView):
    permission_classes = []

    def get(self, request):
        reason = request.query_params.get('reason')
        detail = 'Only authorized @sesame.com.tn accounts are allowed.'
        if reason:
            detail = f'{detail} ({reason})'
        return Response(
            {'error': f'Google login failed. {detail}'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code_input = request.data.get('code', '').strip()
        try:
            record = EmailVerificationCode.objects.get(user=request.user, is_used=False)
        except EmailVerificationCode.DoesNotExist:
            return Response({'error': 'No pending verification code.'}, status=status.HTTP_400_BAD_REQUEST)

        if record.is_expired():
            return Response({'error': 'Code has expired. Please login again to get a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        if record.code != code_input:
            return Response({'error': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        record.is_used = True
        record.save()
        request.user.is_verified = True
        request.user.save(update_fields=['is_verified'])
        return Response({'message': 'Email verified successfully.'})


class ResendCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.is_verified:
            return Response({'message': 'Already verified.'})

        # Do not allow resending codes to accounts that use Google-only auth
        if not request.user.has_usable_password():
            return Response({'error': 'Cannot resend code to Google-authenticated account.'}, status=status.HTTP_400_BAD_REQUEST)

        code = EmailVerificationCode.generate_for(request.user)
        send_verification_email(request.user, code)
        return Response({'message': 'New code sent to your email.'})
