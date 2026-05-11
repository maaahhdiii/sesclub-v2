from django.conf import settings
from django.core.mail import send_mail
from social_core.exceptions import AuthForbidden

from .models import EmailVerificationCode, Role


def send_verification_code(backend, user, is_new=False, *args, **kwargs):
    """
    Called after Google login.
    If user is not yet verified, generate a 6-digit code and email it.
    """
    if backend.name != 'google-oauth2':
        return

    if user.is_verified:
        return

# For Google logins from the whitelisted domain, mark users as verified automatically.
    user.is_verified = True
    user.save(update_fields=['is_verified'])


def reject_non_sesame_domain(strategy, details, backend, *args, **kwargs):
    if backend.name != 'google-oauth2':
        return

    email = (details.get('email') or '').lower()
    if not email.endswith('@sesame.com.tn'):
        raise AuthForbidden(backend, 'Only @sesame.com.tn accounts are allowed.')


def reject_non_student_google_login(backend, user=None, *args, **kwargs):
    if backend.name != 'google-oauth2' or user is None:
        return

    allowed_roles = {Role.STUDENT, Role.ADMIN, Role.CLUB_MANAGER}
    if user.role not in allowed_roles:
        raise AuthForbidden(backend, 'Google login is reserved for authorized SESame accounts.')
