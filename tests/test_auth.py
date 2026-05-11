import pytest


@pytest.mark.django_db
def test_register(client):
    res = client.post(
        '/api/v1/auth/register/',
        {
            'email': 'new@sesame.com.tn',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'strongpass123',
        },
        content_type='application/json',
    )
    assert res.status_code == 201
    assert 'password' not in res.json()


@pytest.mark.django_db
def test_login_returns_tokens(client, django_user_model):
    django_user_model.objects.create_user(
        email='user@test.com',
        password='strongpass123',
    )
    res = client.post(
        '/api/v1/auth/login/',
        {
            'email': 'user@test.com',
            'password': 'strongpass123',
        },
        content_type='application/json',
    )
    assert res.status_code == 200
    assert 'access' in res.json()
    assert 'refresh' in res.json()


@pytest.mark.django_db
def test_protected_route_rejected_without_token(client):
    res = client.get('/api/v1/clubs/')
    assert res.status_code == 401


@pytest.mark.django_db
def test_protected_route_works_with_token(auth_client):
    res = auth_client.get('/api/v1/clubs/')
    assert res.status_code == 200


@pytest.mark.django_db
def test_refresh_token(client, django_user_model):
    django_user_model.objects.create_user(
        email='user2@test.com',
        password='strongpass123',
    )
    login = client.post(
        '/api/v1/auth/login/',
        {
            'email': 'user2@test.com',
            'password': 'strongpass123',
        },
        content_type='application/json',
    )
    refresh = login.json()['refresh']
    res = client.post(
        '/api/v1/auth/refresh/',
        {'refresh': refresh},
        content_type='application/json',
    )
    assert res.status_code == 200
    assert 'access' in res.json()
