from rest_framework import serializers
from .models import Club, ClubMembership
from users.serializers import UserSerializer

class ClubMembershipSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = ClubMembership
        fields = ('id', 'user', 'user_detail', 'club', 'joined_at')
        read_only_fields = ('id', 'joined_at', 'club')

class ClubSerializer(serializers.ModelSerializer):
    memberships = ClubMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Club
        fields = ('club_id', 'name', 'description', 'logo', 'is_active', 'created_at', 'updated_at', 'memberships')
        read_only_fields = ('club_id', 'created_at', 'updated_at')
