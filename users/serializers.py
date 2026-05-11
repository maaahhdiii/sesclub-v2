from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from audit.models import AuditLog
from utils.audit import log_action
from .models import ClubPortalCredential, Role

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        identifier = (attrs.get('email') or '').strip().lower()
        password = attrs.get('password')
        selected_club_id = None
        authenticated_user = None

        user = User.objects.filter(email__iexact=identifier).first()
        if not user and identifier:
            user = User.objects.filter(username=identifier).first()

        if user:
            authenticated_user = authenticate(
                request=self.context.get('request'),
                username=user.username,
                password=password,
            )

        if authenticated_user is None and identifier:
            credential = ClubPortalCredential.objects.select_related('user', 'club').filter(
                username__iexact=identifier,
                is_active=True,
            ).first()
            if credential and credential.check_password(password):
                authenticated_user = credential.user
                selected_club_id = str(credential.club_id)

        if authenticated_user is None:
            raise AuthenticationFailed('No active account found with the given credentials')

        refresh = RefreshToken.for_user(authenticated_user)
        refresh['email'] = authenticated_user.email
        refresh['first_name'] = authenticated_user.first_name
        refresh['is_admin'] = authenticated_user.is_administrator
        self.user = authenticated_user
        request = self.context.get('request')
        log_action(
            authenticated_user,
            AuditLog.AuditAction.USER_LOGIN,
            entity_type='User',
            entity_id=authenticated_user.id,
            ip=getattr(request, 'META', {}).get('REMOTE_ADDR') if request else None,
        )
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'email': authenticated_user.email,
            'first_name': authenticated_user.first_name,
            'is_verified': authenticated_user.is_verified,
            'selected_club_id': selected_club_id,
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'bio', 'avatar', 'date_of_birth', 'phone', 'date_joined')
        read_only_fields = ('id', 'date_joined')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'password')
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data.get('email', '')
        username = email.split('@')[0] if email else None
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=Role.STUDENT,
        )

    def validate_email(self, value):
        email = (value or '').lower()
        if not email.endswith('@sesame.com.tn'):
            raise serializers.ValidationError('Registration is restricted to @sesame.com.tn emails.')
        return email


UserRegistrationSerializer = RegisterSerializer
