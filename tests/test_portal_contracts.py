import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from clubs.models import Club, ClubMembership
from events.models import Event, Review
from users.models import Role


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
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}


@pytest.mark.django_db
def test_event_search_and_status_filters_are_applied():
    manager = create_user(email="manager-filter@sesame.com.tn", role=Role.CLUB_MANAGER)
    viewer = create_user(email="viewer-filter@sesame.com.tn")
    club = Club.objects.create(name="Filter Club", description="desc")
    ClubMembership.objects.create(user=manager, club=club, status="approved", internal_role="president")

    Event.objects.create(
        title="Alpha Active",
        description="desc",
        location="Hall",
        date=timezone.now() + timezone.timedelta(days=1),
        capacity=20,
        status="active",
        club=club,
        organizer=manager,
    )
    Event.objects.create(
        title="Beta Cancelled",
        description="desc",
        location="Hall",
        date=timezone.now() + timezone.timedelta(days=2),
        capacity=20,
        status="cancelled",
        club=club,
        organizer=manager,
    )

    headers = auth_headers_for("viewer-filter@sesame.com.tn")
    search = APIClient().get("/api/v1/events/?search=Alpha", **headers)
    assert search.status_code == 200
    assert search.json()["count"] == 1
    assert search.json()["results"][0]["title"] == "Alpha Active"

    status_filter = APIClient().get("/api/v1/events/?status=active", **headers)
    assert status_filter.status_code == 200
    assert status_filter.json()["count"] == 1
    assert status_filter.json()["results"][0]["status"] == "active"


@pytest.mark.django_db
def test_club_payload_exposes_reviews_for_portals():
    manager = create_user(email="manager-review@sesame.com.tn", role=Role.CLUB_MANAGER)
    reviewer = create_user(email="reviewer@sesame.com.tn", first_name="Sara")
    club = Club.objects.create(name="Review Club", description="desc")
    ClubMembership.objects.create(user=manager, club=club, status="approved", internal_role="president")
    ClubMembership.objects.create(user=reviewer, club=club, status="approved")
    Review.objects.create(user=reviewer, club=club, rating=5, comment="Excellent")

    headers = auth_headers_for("manager-review@sesame.com.tn")
    response = APIClient().get("/api/v1/clubs/", **headers)
    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["reviews"][0]["rating"] == 5
    assert payload["reviews"][0]["user_detail"]["first_name"] == "Sara"


@pytest.mark.django_db
def test_membership_delete_is_not_open_to_unrelated_students():
    manager = create_user(email="manager-membership@sesame.com.tn", role=Role.CLUB_MANAGER)
    member = create_user(email="member@sesame.com.tn")
    intruder = create_user(email="intruder@sesame.com.tn")
    club = Club.objects.create(name="Secure Club", description="desc")
    ClubMembership.objects.create(user=manager, club=club, status="approved", internal_role="president")
    membership = ClubMembership.objects.create(user=member, club=club, status="approved")

    headers = auth_headers_for("intruder@sesame.com.tn")
    response = APIClient().delete(f"/api/v1/memberships/{membership.id}/", **headers)
    assert response.status_code in {403, 404}
    assert ClubMembership.objects.filter(id=membership.id).exists()


@pytest.mark.django_db
def test_audit_payload_contains_frontend_ready_actor_and_ip_fields():
    admin = create_user(email="admin-audit@sesame.com.tn", role=Role.ADMIN)
    headers = auth_headers_for("admin-audit@sesame.com.tn")

    response = APIClient().get("/api/v1/audit-logs/", **headers)
    assert response.status_code == 200
    item = response.json()["results"][0]
    assert item["ip"] == "127.0.0.1"
    assert item["user_email"] == "admin-audit@sesame.com.tn"
