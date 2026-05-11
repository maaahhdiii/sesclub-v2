import pytest

from clubs.models import Club, ClubMembership
from events.models import Event, Review


@pytest.mark.django_db
def test_member_can_review_event(auth_client, auth_user):
    club = Club.objects.create(name='Robotics Club', description='Build things')
    event = Event.objects.create(club=club, title='Hack Night', description='Demo event', capacity=25)
    ClubMembership.objects.create(user=auth_user, club=club, status='approved')

    response = auth_client.post(
        f'/api/v1/events/{event.id}/reviews/',
        {'rating': 5, 'comment': 'Great event!'},
        format='json',
    )

    assert response.status_code == 201
    assert Review.objects.filter(event=event, user=auth_user).count() == 1


@pytest.mark.django_db
def test_non_member_cannot_review_event(auth_client):
    club = Club.objects.create(name='Drama Club', description='Stage time')
    event = Event.objects.create(club=club, title='Show Night', description='Demo event', capacity=25)

    response = auth_client.post(
        f'/api/v1/events/{event.id}/reviews/',
        {'rating': 3, 'comment': 'Okay'},
        format='json',
    )

    assert response.status_code == 403