from rest_framework import serializers
from .models import Event, EventRegistration
from users.serializers import UserSerializer
from clubs.serializers import ClubSerializer

class EventRegistrationSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = EventRegistration
        fields = ('id', 'user', 'user_detail', 'event', 'registered_at')
        read_only_fields = ('id', 'registered_at', 'event', 'user')

class EventSerializer(serializers.ModelSerializer):
    club_detail = ClubSerializer(source='club', read_only=True)
    organizer_username = serializers.ReadOnlyField(source='organizer.username')
    registered_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    registrations = EventRegistrationSerializer(many=True, read_only=True) # Maybe we shouldn't nest this for all events to save bandwidth, but ok for now

    class Meta:
        model = Event
        fields = ('id', 'title', 'description', 'club', 'club_detail', 'organizer', 'organizer_username', 
                  'location', 'date', 'end_date', 'capacity', 'status', 'created_at', 'updated_at', 
                  'registered_count', 'is_full', 'registrations')
        read_only_fields = ('id', 'created_at', 'updated_at', 'organizer')
