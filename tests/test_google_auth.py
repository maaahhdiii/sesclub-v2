import pytest
from social_core.exceptions import AuthForbidden
from django.contrib.auth import get_user_model

from users.models import EmailVerificationCode
from users.models import Role
from users.pipeline import reject_non_sesame_domain


@pytest.mark.django_db
def test_unverified_user_cannot_access_clubs(unverified_auth_client):
    res = unverified_auth_client.get('/api/v1/clubs/')
    assert res.status_code == 403


@pytest.mark.django_db
def test_verified_user_can_access_clubs(verified_auth_client):
    res = verified_auth_client.get('/api/v1/clubs/')
    assert res.status_code == 200


@pytest.mark.django_db
def test_correct_code_verifies_user(unverified_auth_client, google_user):
    code = EmailVerificationCode.generate_for(google_user)
    res = unverified_auth_client.post('/api/v1/auth/verify-code/', {'code': code}, content_type='application/json')
    assert res.status_code == 200
    google_user.refresh_from_db()
    assert google_user.is_verified is True


@pytest.mark.django_db
def test_wrong_code_rejected(unverified_auth_client):
    res = unverified_auth_client.post('/api/v1/auth/verify-code/', {'code': '000000'}, content_type='application/json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_non_sesame_domain_rejected():
    class Backend:
        name = 'google-oauth2'

    with pytest.raises(Exception) as exc_info:
        reject_non_sesame_domain(None, {'email': 'person@other.com'}, Backend())

    assert exc_info.value.__class__.__name__ == 'AuthForbidden'


@pytest.mark.django_db
def test_google_callback_redirects_to_error_on_authforbidden(client, monkeypatch):
    def raise_forbidden(*args, **kwargs):
        raise AuthForbidden('google-oauth2', 'Google login is reserved for student and administrator accounts.')

    monkeypatch.setattr('users.views.social_complete', raise_forbidden)

    response = client.get('/api/v1/auth/google/complete/google-oauth2/')

    assert response.status_code == 302
    assert response['Location'].startswith('/api/v1/auth/google/error/?reason=')


@pytest.mark.django_db
def test_google_student_login_sets_session_intent(client):
    response = client.get('/api/v1/auth/google/login/student/')

    assert response.status_code == 302
    assert response['Location'] == '/api/v1/auth/google/login/google-oauth2/'
    assert client.session.get('google_portal_target') == 'student'


@pytest.mark.django_db
def test_google_club_login_sets_session_intent(client):
    response = client.get('/api/v1/auth/google/login/club/?club_id=abc123')

    assert response.status_code == 302
    assert response['Location'] == '/api/v1/auth/google/login/google-oauth2/'
    assert client.session.get('google_portal_target') == 'club'
    assert client.session.get('google_club_id') == 'abc123'


@pytest.mark.django_db
def test_google_club_login_uses_referrer_club_id_when_query_missing(client):
    response = client.get(
        '/api/v1/auth/google/login/club/',
        HTTP_REFERER='http://127.0.0.1:8000/club/?club_id=from-referrer-1',
    )

    assert response.status_code == 302
    assert response['Location'] == '/api/v1/auth/google/login/google-oauth2/'
    assert client.session.get('google_portal_target') == 'club'
    assert client.session.get('google_club_id') == 'from-referrer-1'


@pytest.mark.django_db
def test_google_success_respects_student_intent_for_club_manager(client):
    user_model = get_user_model()
    manager = user_model.objects.create_user(
        username='manager-intent',
        email='manager-intent@sesame.com.tn',
        password='password',
        role=Role.CLUB_MANAGER,
        is_verified=True,
    )
    client.force_login(manager)
    session = client.session
    session['google_portal_target'] = 'student'
    session.save()

    response = client.get('/api/v1/auth/google/success/')

    assert response.status_code == 200
    assert '/student/' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_google_success_respects_club_intent_for_student(client, google_user):
    google_user.role = Role.STUDENT
    google_user.is_verified = True
    google_user.save(update_fields=['role', 'is_verified'])
    client.force_login(google_user)
    session = client.session
    session['google_portal_target'] = 'club'
    session['google_club_id'] = 'club-xyz-123'
    session.save()

    response = client.get('/api/v1/auth/google/success/')

    assert response.status_code == 200
    body = response.content.decode('utf-8')
    assert '/club/?club_id=club-xyz-123' in body