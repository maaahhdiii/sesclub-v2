from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Club, ClubMembership
from users.serializers import UserSerializer


User = get_user_model()


class ClubReviewSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    rating = serializers.IntegerField(read_only=True)
    comment = serializers.CharField(read_only=True)
    user = serializers.UUIDField(read_only=True)
    user_detail = UserSerializer(read_only=True)


class ClubMembershipSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    user_detail = UserSerializer(source='user', read_only=True)
    user_email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = ClubMembership
        fields = ('id', 'user', 'user_email', 'user_detail', 'club', 'joined_at', 'internal_role', 'status')
        read_only_fields = ('id', 'joined_at')
        validators = []
    def validate(self, attrs):
        attrs = super().validate(attrs)
        user_email = attrs.pop('user_email', None)
        if user_email and 'user' not in attrs:
            user = self.context['request'].user.__class__.objects.filter(email=user_email.lower()).first()
            if user is None:
                raise serializers.ValidationError({'user_email': 'No student account was found with this email.'})
            attrs['user'] = user
        # Only administrators can directly assign president via memberships API.
        if attrs.get('internal_role') == 'president':
            request_user = getattr(self.context.get('request'), 'user', None)
            if not (request_user and getattr(request_user, 'is_administrator', False)):
                raise serializers.ValidationError({'internal_role': 'Only administrators can assign a president directly.'})
        if attrs.get('user') and attrs.get('club'):
            if ClubMembership.objects.filter(user=attrs['user'], club=attrs['club']).exists():
                raise serializers.ValidationError({'user': 'This student is already a member of the club.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('user_email', None)
        return super().create(validated_data)

class ClubSerializer(serializers.ModelSerializer):
    memberships = ClubMembershipSerializer(many=True, read_only=True)
    id = serializers.UUIDField(source='club_id', read_only=True)
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = ('id', 'name', 'description', 'logo', 'is_active', 'created_at', 'updated_at', 'memberships', 'reviews')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_reviews(self, obj):
        payload = [
            {
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'user': review.user_id,
                'user_detail': UserSerializer(review.user).data,
            }
            for review in obj.reviews.select_related('user').all()
        ]
        return ClubReviewSummarySerializer(payload, many=True).data
