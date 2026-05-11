from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Club, ClubMembership
from users.serializers import UserSerializer
from django.core.files.uploadedfile import InMemoryUploadedFile
import io
try:
    from PIL import Image, UnidentifiedImageError
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


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

    def validate(self, attrs):
        # Validate uploaded logo if present
        logo = attrs.get('logo')
        if logo:
            # Basic content-type/size checks
            content_type = getattr(logo, 'content_type', '')
            if content_type and not content_type.startswith('image/'):
                raise serializers.ValidationError({'logo': 'Uploaded file must be an image.'})
            max_bytes = 2 * 1024 * 1024  # 2 MB
            size = getattr(logo, 'size', None)
            if size and size > max_bytes:
                raise serializers.ValidationError({'logo': 'Image file too large (max 2 MB).'})

            # If Pillow is available, attempt to normalize / resize the image to a reasonable width
            if PIL_AVAILABLE and isinstance(logo, InMemoryUploadedFile):
                try:
                    logo.file.seek(0)
                    img = Image.open(logo.file)
                    img = img.convert('RGBA') if img.mode in ('P', 'LA') else img.convert('RGB')
                    max_width = 1200
                    if img.width > max_width:
                        ratio = max_width / float(img.width)
                        new_height = int(float(img.height) * ratio)
                        img = img.resize((max_width, new_height), Image.LANCZOS)
                        out = io.BytesIO()
                        img_format = 'JPEG' if img.mode == 'RGB' else 'PNG'
                        img.save(out, format=img_format, quality=85)
                        out.seek(0)
                        new_file = InMemoryUploadedFile(out, 'logo', logo.name, f'image/{img_format.lower()}', out.getbuffer().nbytes, None)
                        attrs['logo'] = new_file
                except UnidentifiedImageError:
                    raise serializers.ValidationError({'logo': 'Uploaded file is not a valid image.'})
                except Exception:
                    # If processing fails, fall back to accepting the original file
                    pass
            # Also generate a small thumbnail if possible
            if PIL_AVAILABLE and isinstance(attrs.get('logo'), InMemoryUploadedFile):
                try:
                    attrs['logo'].file.seek(0)
                    img = Image.open(attrs['logo'].file)
                    img = img.convert('RGB')
                    thumb_size = (300, 300)
                    img.thumbnail(thumb_size, Image.LANCZOS)
                    out = io.BytesIO()
                    img.save(out, format='JPEG', quality=80)
                    out.seek(0)
                    thumb_file = InMemoryUploadedFile(out, 'logo_thumbnail', f"thumb_{attrs['logo'].name}", 'image/jpeg', out.getbuffer().nbytes, None)
                    attrs['logo_thumbnail'] = thumb_file
                except Exception:
                    pass
        return super().validate(attrs)
