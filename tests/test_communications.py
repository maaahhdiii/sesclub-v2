from communications.models import Conversation, Message


def test_create_conversation(auth_client):
    response = auth_client.post('/api/v1/conversations/', {}, format='json')

    assert response.status_code == 201
    assert Conversation.objects.count() == 1


def test_send_message(auth_client):
    conversation_response = auth_client.post('/api/v1/conversations/', {}, format='json')
    conversation_id = conversation_response.data['id']

    response = auth_client.post(
        f'/api/v1/conversations/{conversation_id}/messages/',
        {'body': 'Hello there'},
        format='json',
    )

    assert response.status_code == 201
    assert Message.objects.filter(conversation_id=conversation_id).count() == 1
