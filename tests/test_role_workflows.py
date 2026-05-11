import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from app_requests.models import Request
from clubs.models import Club, ClubMembership
from users.models import ClubPortalCredential, Role
from users.pipeline import reject_non_student_google_login


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
    response = client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_treating_club_creation_request_creates_club_and_promotes_student():
    admin = create_user(email="admin-workflow@sesame.com.tn", role=Role.ADMIN)
    student = create_user(email="student-workflow@sesame.com.tn")
    request_item = Request.objects.create(
        request_type=Request.RequestType.CLUB_CREATION,
        title="Robotics Club",
        description="Build robots",
        user=student,
        metadata={"club_category": "Technology"},
    )

    headers = auth_headers_for("admin-workflow@sesame.com.tn")
    response = APIClient().patch(
        f"/api/v1/requests/{request_item.request_id}/update_status/",
        {"status": Request.RequestStatus.TREATED},
        format="json",
        **headers,
    )

    assert response.status_code == 200
    student.refresh_from_db()
    request_item.refresh_from_db()
    club = Club.objects.get(name="Robotics Club")
    membership = ClubMembership.objects.get(user=student, club=club)
    credential = ClubPortalCredential.objects.get(user=student, club=club)
    assert student.role == Role.CLUB_MANAGER
    assert '@' in credential.username
    assert membership.internal_role == "president"
    assert membership.status == "approved"
    assert request_item.metadata["created_club_id"] == str(club.club_id)
    assert request_item.metadata["club_portal_username"] == credential.username
    assert request_item.metadata["credentials_sent"] is True
    assert len(mail.outbox) == 1
    email_body = mail.outbox[0].body
    assert f"Username: {credential.username}" in email_body
    assert f"club_id={club.club_id}" in email_body

    temp_password = next(
        line.split("Password: ", 1)[1]
        for line in email_body.splitlines()
        if line.startswith("Password: ")
    )
    login_response = APIClient().post(
        "/api/v1/auth/login/",
        {"email": credential.username, "password": temp_password},
        format="json",
    )
    assert login_response.status_code == 200
    assert login_response.json()["selected_club_id"] == str(club.club_id)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_same_user_can_have_multiple_approved_club_creation_requests():
    create_user(email="admin-multi@sesame.com.tn", role=Role.ADMIN)
    student = create_user(email="multi-owner@sesame.com.tn")
    first_request = Request.objects.create(
        request_type=Request.RequestType.CLUB_CREATION,
        title="Robotics Alpha",
        description="First club",
        user=student,
    )
    second_request = Request.objects.create(
        request_type=Request.RequestType.CLUB_CREATION,
        title="Robotics Beta",
        description="Second club",
        user=student,
    )

    headers = auth_headers_for("admin-multi@sesame.com.tn")
    first_response = APIClient().patch(
        f"/api/v1/requests/{first_request.request_id}/update_status/",
        {"status": Request.RequestStatus.TREATED},
        format="json",
        **headers,
    )
    second_response = APIClient().patch(
        f"/api/v1/requests/{second_request.request_id}/update_status/",
        {"status": Request.RequestStatus.TREATED},
        format="json",
        **headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    student.refresh_from_db()
    first_request.refresh_from_db()
    second_request.refresh_from_db()
    first_club = Club.objects.get(club_id=first_request.metadata["created_club_id"])
    second_club = Club.objects.get(club_id=second_request.metadata["created_club_id"])
    first_credential = ClubPortalCredential.objects.get(user=student, club=first_club)
    second_credential = ClubPortalCredential.objects.get(user=student, club=second_club)

    assert student.role == Role.CLUB_MANAGER
    assert '@' in first_credential.username
    assert '@' in second_credential.username
    assert first_credential.username != second_credential.username
    assert Club.objects.filter(name="Robotics Alpha").exists()
    assert Club.objects.filter(name="Robotics Beta").exists()
    assert ClubMembership.objects.filter(user=student, internal_role="president", status="approved").count() == 2
    assert first_request.metadata["created_club_id"] != second_request.metadata["created_club_id"]
    assert first_request.metadata["credentials_sent"] is True
    assert second_request.metadata["credentials_sent"] is True
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_president_can_add_student_member_by_email():
    president = create_user(email="president@sesame.com.tn", role=Role.CLUB_MANAGER)
    student = create_user(email="newmember@sesame.com.tn")
    club = Club.objects.create(name="AI Club", description="desc")
    ClubMembership.objects.create(user=president, club=club, status="approved", internal_role="president")

    headers = auth_headers_for("president@sesame.com.tn")
    response = APIClient().post(
        "/api/v1/memberships/",
        {"club": str(club.club_id), "user_email": "newmember@sesame.com.tn", "internal_role": "member"},
        format="json",
        **headers,
    )

    assert response.status_code == 201
    membership = ClubMembership.objects.get(user=student, club=club)
    assert membership.status == "approved"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_adding_member_sends_welcome_email_with_portal_url():
    president = create_user(email="president-welcome@sesame.com.tn", role=Role.CLUB_MANAGER)
    student = create_user(email="welcome-member@sesame.com.tn")
    club = Club.objects.create(name="Cloud Club", description="desc")
    ClubMembership.objects.create(user=president, club=club, status="approved", internal_role="president")

    headers = auth_headers_for("president-welcome@sesame.com.tn")
    response = APIClient().post(
        "/api/v1/memberships/",
        {"club": str(club.club_id), "user_email": "welcome-member@sesame.com.tn", "internal_role": "member"},
        format="json",
        **headers,
    )

    assert response.status_code == 201
    assert len(mail.outbox) >= 1
    assert "Welcome to Cloud Club" in mail.outbox[-1].subject
    assert f"http://127.0.0.1:8000/club/?club_id={club.club_id}" in mail.outbox[-1].body
    assert "Google sign-in" in mail.outbox[-1].body


@pytest.mark.django_db
def test_club_manager_can_list_verified_students_for_member_search():
    manager = create_user(email="manager-list@sesame.com.tn", role=Role.CLUB_MANAGER)
    student_one = create_user(email="search-one@sesame.com.tn", role=Role.STUDENT, is_verified=True)
    create_user(email="search-two@sesame.com.tn", role=Role.STUDENT, is_verified=False)

    headers = auth_headers_for("manager-list@sesame.com.tn")
    response = APIClient().get("/api/v1/users/", format="json", **headers)

    assert response.status_code == 200
    payload = response.json()
    records = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
    emails = {record["email"] for record in records}
    assert student_one.email in emails
    assert manager.email not in emails


@pytest.mark.django_db
def test_president_can_add_club_manager_to_another_club():
    admin = create_user(email="admin-add-manager@sesame.com.tn", role=Role.ADMIN)
    manager = create_user(email="manager-member@sesame.com.tn", role=Role.CLUB_MANAGER)
    club = Club.objects.create(name="Data Club", description="desc")

    headers = auth_headers_for("admin-add-manager@sesame.com.tn")
    response = APIClient().post(
        "/api/v1/memberships/",
        {"club": str(club.club_id), "user_email": "manager-member@sesame.com.tn", "internal_role": "president"},
        format="json",
        **headers,
    )

    assert response.status_code == 201
    membership = ClubMembership.objects.get(user=manager, club=club)
    assert membership.status == "approved"
    assert ClubPortalCredential.objects.filter(user=manager, club=club).exists()
    assert len(mail.outbox) >= 1
    assert "Club Manager Access" in mail.outbox[-1].subject
    assert f"club_id={club.club_id}" in mail.outbox[-1].body


@pytest.mark.django_db
def test_president_cannot_add_admin_account_as_member():
    president = create_user(email="president2@sesame.com.tn", role=Role.CLUB_MANAGER)
    admin = create_user(email="admin-member@sesame.com.tn", role=Role.ADMIN)
    club = Club.objects.create(name="Security Club", description="desc")
    ClubMembership.objects.create(user=president, club=club, status="approved", internal_role="president")

    headers = auth_headers_for("president2@sesame.com.tn")
    response = APIClient().post(
        "/api/v1/memberships/",
        {"club": str(club.club_id), "user_email": "admin-member@sesame.com.tn", "internal_role": "member"},
        format="json",
        **headers,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_club_manager_google_login_is_allowed():
    manager = create_user(email="manager-google@sesame.com.tn", role=Role.CLUB_MANAGER)

    class Backend:
        name = "google-oauth2"

    # Club managers are first-class portal users and may authenticate with Google.
    assert reject_non_student_google_login(Backend(), user=manager) is None
