from rest_framework import serializers
from .models import Event, EventRegistration, Review
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
    registered_count = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    registrations = EventRegistrationSerializer(many=True, read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'title', 'description', 'club', 'club_detail', 'organizer', 'organizer_username',
                  'location', 'date', 'capacity', 'status', 'registered_count', 'is_full', 'registrations')
        read_only_fields = ('id', 'organizer')

    def get_registered_count(self, obj):
        return obj.registrations.count()

    def get_is_full(self, obj):
        return obj.capacity > 0 and obj.registrations.count() >= obj.capacity


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'rating', 'comment', 'user', 'event', 'club')
        read_only_fields = ('id', 'user', 'event', 'club')
