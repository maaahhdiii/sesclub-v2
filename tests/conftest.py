import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from users.models import Role

User = get_user_model()


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username='student-user',
        email='student-user@example.com',
        password='password',
        role=Role.STUDENT,
        is_verified=True,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin-user',
        email='admin-user@example.com',
        password='password',
        role=Role.ADMIN,
        is_verified=True,
    )


@pytest.fixture
def auth_client(auth_user):
    client = APIClient()
    client.force_authenticate(user=auth_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def verified_auth_client(auth_user):
    client = APIClient()
    client.force_authenticate(user=auth_user)
    return client


@pytest.fixture
def google_user(db):
    return User.objects.create_user(
        username='test',
        email='test@sesame.com.tn',
        password='password',
        role=Role.STUDENT,
        is_verified=False,
    )


@pytest.fixture
def unverified_auth_client(google_user):
    client = APIClient()
    client.force_authenticate(user=google_user)
    return client
