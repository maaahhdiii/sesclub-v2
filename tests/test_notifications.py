import pytest

from communications.models import Notification
from clubs.models import Club


@pytest.mark.django_db
def test_join_club_creates_notification(auth_client, auth_user):
    club = Club.objects.create(name='Music Club', description='A club for music lovers')

    response = auth_client.post(f'/api/v1/clubs/{club.club_id}/join/', format='json')

    assert response.status_code == 201
    assert Notification.objects.filter(user=auth_user, title='Club Joined').exists()


@pytest.mark.django_db
def test_notifications_list(auth_client, auth_user):
    Notification.objects.create(user=auth_user, title='Test notification', body='Body')

    response = auth_client.get('/api/v1/notifications/')

    assert response.status_code == 200
    assert response.json()['count'] == 1