import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from app_requests.models import Request
from clubs.models import Club, ClubMembership
from communications.models import Conversation, Notification
from events.models import Event, Review
from users.models import EmailVerificationCode, Role


User = get_user_model()


def create_user(*, email, password="TestPass123", role=Role.STUDENT, is_verified=True, **extra):
    username = extra.pop("username", email.split("@")[0])
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role,
        is_verified=is_verified,
        first_name=extra.pop("first_name", "Test"),
        last_name=extra.pop("last_name", "User"),
        **extra,
    )


def auth_headers_for(email, password="TestPass123"):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    return response, {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_auth_flow_validation():
    client = APIClient()

    register = client.post(
        "/api/v1/auth/register/",
        {
            "email": "testuser@sesame.com.tn",
            "first_name": "Test",
            "last_name": "User",
            "password": "TestPass123",
        },
        format="json",
    )
    assert register.status_code == 201
    verification_code = register.json().get("verification_code")
    assert "password" not in register.json()
    assert len(mail.outbox) == 1
    if verification_code is None:
        verification_code = EmailVerificationCode.objects.get(user__email="testuser@sesame.com.tn").code

    rejected = client.post(
        "/api/v1/auth/register/",
        {
            "email": "hacker@gmail.com",
            "first_name": "X",
            "last_name": "Y",
            "password": "TestPass123",
        },
        format="json",
    )
    assert rejected.status_code == 400
    assert "@sesame.com.tn" in str(rejected.json())

    login, headers = auth_headers_for("testuser@sesame.com.tn")
    assert login.status_code == 200
    assert login.json()["is_verified"] is False
    assert "password" not in login.json()

    blocked = client.get("/api/v1/clubs/", **headers)
    assert blocked.status_code == 403

    wrong_code = client.post("/api/v1/auth/verify-code/", {"code": "000000"}, format="json", **headers)
    assert wrong_code.status_code == 400
    assert wrong_code.json()["error"] == "Invalid code."

    verify = client.post(
        "/api/v1/auth/verify-code/",
        {"code": verification_code},
        format="json",
        **headers,
    )
    assert verify.status_code == 200
    assert User.objects.get(email="testuser@sesame.com.tn").is_verified is True

    allowed = client.get("/api/v1/clubs/", **headers)
    assert allowed.status_code == 200
    assert {"count", "results"}.issubset(allowed.json().keys())

    refresh = client.post("/api/v1/auth/refresh/", {"refresh": login.json()["refresh"]}, format="json")
    assert refresh.status_code == 200
    assert "access" in refresh.json()

    unverified = create_user(email="resend@sesame.com.tn", is_verified=False)
    resend_login, resend_headers = auth_headers_for("resend@sesame.com.tn")
    assert resend_login.status_code == 200
    resend = client.post("/api/v1/auth/resend-code/", format="json", **resend_headers)
    assert resend.status_code == 200
    assert EmailVerificationCode.objects.filter(user=unverified).exists()

    assert "sesame.com.tn" in settings.SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS


@pytest.mark.django_db
def test_clubs_validation():
    regular = create_user(email="regular@sesame.com.tn")
    admin = create_user(email="admin@sesame.com.tn", role=Role.ADMIN)
    club = Club.objects.create(name="Alpha Club", description="A test club", is_active=True)
    Club.objects.create(name="Dormant Club", description="Inactive", is_active=False)

    regular_login, regular_headers = auth_headers_for("regular@sesame.com.tn")
    admin_login, admin_headers = auth_headers_for("admin@sesame.com.tn")
    assert regular_login.status_code == 200
    assert admin_login.status_code == 200

    listing = APIClient().get("/api/v1/clubs/", **regular_headers)
    assert listing.status_code == 200
    assert {"count", "results"}.issubset(listing.json().keys())

    regular_create = APIClient().post(
        "/api/v1/clubs/",
        {"name": "Regular Club", "description": "Nope", "is_active": True},
        format="json",
        **regular_headers,
    )
    assert regular_create.status_code == 403

    admin_create = APIClient().post(
        "/api/v1/clubs/",
        {"name": "Admin Club", "description": "Allowed", "is_active": True},
        format="json",
        **admin_headers,
    )
    assert admin_create.status_code == 201

    join = APIClient().post(f"/api/v1/clubs/{club.club_id}/join/", format="json", **regular_headers)
    assert join.status_code in {200, 201}

    join_again = APIClient().post(f"/api/v1/clubs/{club.club_id}/join/", format="json", **regular_headers)
    assert join_again.status_code in {200, 400}

    leave = APIClient().delete(f"/api/v1/clubs/{club.club_id}/leave/", **regular_headers)
    assert leave.status_code in {200, 204}

    search = APIClient().get("/api/v1/clubs/?search=Alpha", **regular_headers)
    assert search.status_code == 200
    assert search.json()["count"] == 1

    filtered = APIClient().get("/api/v1/clubs/?is_active=true", **regular_headers)
    assert filtered.status_code == 200
    assert all(item["is_active"] is True for item in filtered.json()["results"])

    ClubMembership.objects.create(user=regular, club=club, status="approved")
    review = APIClient().post(
        f"/api/v1/clubs/{club.club_id}/reviews/",
        {"rating": 5, "comment": "Great club"},
        format="json",
        **regular_headers,
    )
    assert review.status_code == 201

    outsider = create_user(email="outsider@sesame.com.tn")
    _, outsider_headers = auth_headers_for("outsider@sesame.com.tn")
    review_blocked = APIClient().post(
        f"/api/v1/clubs/{club.club_id}/reviews/",
        {"rating": 5, "comment": "Sneaky"},
        format="json",
        **outsider_headers,
    )
    assert review_blocked.status_code == 403

    duplicate = APIClient().post(
        f"/api/v1/clubs/{club.club_id}/reviews/",
        {"rating": 5, "comment": "Again"},
        format="json",
        **regular_headers,
    )
    assert duplicate.status_code == 400


@pytest.mark.django_db
def test_events_requests_notifications_messaging_and_security_validation():
    admin = create_user(email="admin2@sesame.com.tn", role=Role.ADMIN)
    manager = create_user(email="manager@sesame.com.tn", role=Role.CLUB_MANAGER)
    regular = create_user(email="student@sesame.com.tn")
    other = create_user(email="other@sesame.com.tn")
    club = Club.objects.create(name="Builders Club", description="Build")
    ClubMembership.objects.create(user=manager, club=club, status="approved", internal_role="president")
    ClubMembership.objects.create(user=regular, club=club, status="approved")
    event = Event.objects.create(
        title="Test Event",
        description="desc",
        location="Room A",
        date=timezone.now() + timezone.timedelta(days=10),
        capacity=30,
        status="active",
        club=club,
        organizer=manager,
    )

    _, admin_headers = auth_headers_for("admin2@sesame.com.tn")
    _, manager_headers = auth_headers_for("manager@sesame.com.tn")
    _, regular_headers = auth_headers_for("student@sesame.com.tn")
    _, other_headers = auth_headers_for("other@sesame.com.tn")

    event_list = APIClient().get("/api/v1/events/", **regular_headers)
    assert event_list.status_code == 200

    regular_event_create = APIClient().post(
        "/api/v1/events/",
        {
            "title": "Blocked Event",
            "description": "desc",
            "location": "Room A",
            "date": "2026-09-01T10:00:00Z",
            "capacity": 30,
            "status": "active",
            "club": str(club.club_id),
        },
        format="json",
        **regular_headers,
    )
    assert regular_event_create.status_code == 403

    manager_event_create = APIClient().post(
        "/api/v1/events/",
        {
            "title": "Manager Event",
            "description": "desc",
            "location": "Room A",
            "date": "2026-09-01T10:00:00Z",
            "capacity": 30,
            "status": "active",
            "club": str(club.club_id),
        },
        format="json",
        **manager_headers,
    )
    assert manager_event_create.status_code == 201

    register = APIClient().post(f"/api/v1/events/{event.id}/register/", format="json", **regular_headers)
    assert register.status_code in {200, 201}

    register_again = APIClient().post(f"/api/v1/events/{event.id}/register/", format="json", **regular_headers)
    assert register_again.status_code == 400

    unregister = APIClient().delete(f"/api/v1/events/{event.id}/unregister/", **regular_headers)
    assert unregister.status_code in {200, 204}

    status_filter = APIClient().get("/api/v1/events/?status=active", **regular_headers)
    assert status_filter.status_code == 200
    assert all(item["status"] == "active" for item in status_filter.json()["results"])

    search = APIClient().get("/api/v1/events/?search=Test", **regular_headers)
    assert search.status_code == 200
    assert search.json()["count"] >= 1

    create_request = APIClient().post(
        "/api/v1/requests/",
        {
            "request_type": "CLUB_CREATION",
            "title": "New Club",
            "description": "I want to start a coding club",
            "metadata": {},
        },
        format="json",
        **regular_headers,
    )
    assert create_request.status_code == 201
    request_id = create_request.json()["id"]

    own_requests = APIClient().get("/api/v1/requests/", **regular_headers)
    assert own_requests.status_code == 200
    assert own_requests.json()["count"] == 1

    admin_requests = APIClient().get("/api/v1/requests/", **admin_headers)
    assert admin_requests.status_code == 200
    assert admin_requests.json()["count"] >= 1

    regular_status_update = APIClient().patch(
        f"/api/v1/requests/{request_id}/update_status/",
        {"status": "TREATED"},
        format="json",
        **regular_headers,
    )
    assert regular_status_update.status_code == 403

    admin_status_update = APIClient().patch(
        f"/api/v1/requests/{request_id}/update_status/",
        {"status": "TREATED"},
        format="json",
        **admin_headers,
    )
    assert admin_status_update.status_code == 200

    notifications = APIClient().get("/api/v1/notifications/", **regular_headers)
    assert notifications.status_code == 200
    assert notifications.json()["count"] >= 1
    notification_id = notifications.json()["results"][0]["id"]

    mark_read = APIClient().patch(f"/api/v1/notifications/{notification_id}/read/", format="json", **regular_headers)
    assert mark_read.status_code == 200

    conversation = APIClient().post(
        "/api/v1/conversations/",
        {"participants": [str(other.id)]},
        format="json",
        **regular_headers,
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]
    assert Conversation.objects.get(conversation_id=conversation_id).participants.filter(id=other.id).exists()

    message = APIClient().post(
        f"/api/v1/conversations/{conversation_id}/messages/",
        {"body": "Hello!"},
        format="json",
        **regular_headers,
    )
    assert message.status_code == 201

    messages = APIClient().get(f"/api/v1/conversations/{conversation_id}/messages/", **regular_headers)
    assert messages.status_code == 200
    assert messages.json()["count"] == 1

    own_conversations = APIClient().get("/api/v1/conversations/", **regular_headers)
    assert own_conversations.status_code == 200
    assert own_conversations.json()["count"] == 1

    audit_admin = APIClient().get("/api/v1/audit-logs/", **admin_headers)
    assert audit_admin.status_code == 200

    audit_regular = APIClient().get("/api/v1/audit-logs/", **regular_headers)
    assert audit_regular.status_code == 403

    no_token_checks = [
        "/api/v1/clubs/",
        "/api/v1/events/",
        "/api/v1/requests/",
        "/api/v1/notifications/",
        "/api/v1/audit-logs/",
    ]
    for path in no_token_checks:
        assert APIClient().get(path).status_code == 401

    expired = AccessToken.for_user(regular)
    expired.set_exp(lifetime=timezone.timedelta(seconds=-1))
    expired_response = APIClient().get(
        "/api/v1/clubs/",
        HTTP_AUTHORIZATION=f"Bearer {str(expired)}",
    )
    assert expired_response.status_code == 401

    scheme, token = manager_headers["HTTP_AUTHORIZATION"].split(" ", 1)
    token_parts = token.split(".")
    token_parts[-1] = ("x" if token_parts[-1][0] != "x" else "y") + token_parts[-1][1:]
    tampered = f"{scheme} {'.'.join(token_parts)}"
    tampered_response = APIClient().get("/api/v1/clubs/", HTTP_AUTHORIZATION=tampered)
    assert tampered_response.status_code == 401

    empty_register = APIClient().post("/api/v1/auth/register/", {}, format="json")
    assert empty_register.status_code == 400

    invalid_rating = APIClient().post(
        f"/api/v1/events/{event.id}/reviews/",
        {"rating": 10, "comment": "Too high"},
        format="json",
        **regular_headers,
    )
    assert invalid_rating.status_code == 400

    invalid_request_type = APIClient().post(
        "/api/v1/requests/",
        {"request_type": "INVALID_TYPE", "title": "X", "description": "Y"},
        format="json",
        **regular_headers,
    )
    assert invalid_request_type.status_code == 400

    other_request = Request.objects.create(
        request_type=Request.RequestType.CLAIM,
        title="Other request",
        description="Secret",
        user=other,
    )
    forbidden_request = APIClient().get(f"/api/v1/requests/{other_request.request_id}/", **regular_headers)
    assert forbidden_request.status_code in {403, 404}

    paginated = APIClient().get("/api/v1/clubs/?page=1&page_size=5", **regular_headers)
    assert paginated.status_code == 200
    assert {"count", "next", "previous", "results"}.issubset(paginated.json().keys())
