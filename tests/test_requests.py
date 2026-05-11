from app_requests.models import Request
from users.models import Role


def test_user_can_create_request(auth_client):
    response = auth_client.post(
        '/api/v1/requests/',
        {
            'request_type': 'CLUB CREATION',
            'title': 'Create a robotics club',
            'description': 'We need a robotics club on campus.',
        },
        format='json',
    )

    assert response.status_code == 201
    assert Request.objects.count() == 1


def test_admin_request_list_includes_requester_details(auth_client, admin_client, auth_user):
    Request.objects.create(
        request_type='CLUB CREATION',
        title='Create a robotics club',
        description='We need a robotics club on campus.',
        user=auth_user,
    )

    response = admin_client.get('/api/v1/requests/')

    assert response.status_code == 200
    payload = response.data['results'][0] if 'results' in response.data else response.data[0]
    assert payload['user']['id'] == str(auth_user.id)
    assert payload['user']['email'] == auth_user.email


def test_only_admin_can_update_status(auth_client, admin_client):
    created = auth_client.post(
        '/api/v1/requests/',
        {
            'request_type': 'CLUB CREATION',
            'title': 'Create a chess club',
            'description': 'Students want a chess club.',
        },
        format='json',
    )
    request_id = created.data['id']

    forbidden = auth_client.patch(
        f'/api/v1/requests/{request_id}/update_status/',
        {'status': 'TREATED'},
        format='json',
    )
    assert forbidden.status_code == 403

    allowed = admin_client.patch(
        f'/api/v1/requests/{request_id}/update_status/',
        {'status': 'TREATED'},
        format='json',
    )
    assert allowed.status_code == 200
    assert allowed.data['status'] == 'TREATED'


def test_club_manager_can_create_request_and_admin_can_see_it(db, admin_client):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    user_model = get_user_model()
    manager = user_model.objects.create_user(
        username='manager-request',
        email='manager-request@sesame.com.tn',
        password='password',
        role=Role.CLUB_MANAGER,
        is_verified=True,
    )

    manager_client = APIClient()
    manager_client.force_authenticate(user=manager)

    response = manager_client.post(
        '/api/v1/requests/',
        {
            'request_type': 'CLUB_CREATION',
            'title': 'Second Club Proposal',
            'description': 'Manager-created request should be visible to admin.',
        },
        format='json',
    )

    assert response.status_code == 201

    admin_response = admin_client.get('/api/v1/requests/')
    assert admin_response.status_code == 200
    assert admin_response.data['count'] >= 1
