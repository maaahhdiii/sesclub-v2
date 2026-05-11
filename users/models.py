import uuid
import random
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class CustomUserManager(DjangoUserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        if not username and email:
            username = email.split('@')[0]
        if not username:
            raise ValueError('The username or email must be set')
        if not email:
            email = f'{username}@example.com'
        return super().create_user(username=username, email=email, password=password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        if not username and email:
            username = email.split('@')[0]
        if not username:
            raise ValueError('The username or email must be set')
        if not email:
            email = f'{username}@example.com'
        return super().create_superuser(username=username, email=email, password=password, **extra_fields)


class Privelege(models.Model):
    privelege_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=255)
    action_description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Privilege'
        verbose_name_plural = 'Privileges'

    def __str__(self):
        return self.action


class Role(models.Model):
    ADMIN = 'administrator'
    CLUB_MANAGER = 'club_manager'
    STUDENT = 'student'

    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    privileges = models.ManyToManyField(Privelege, related_name='roles', blank=True)

    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom User model matching 'Utilisateur' from the class diagram.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    role = models.CharField(
        max_length=50,
        choices=[
            (Role.ADMIN, 'Administrator'),
            (Role.CLUB_MANAGER, 'Club Manager'),
            (Role.STUDENT, 'Student'),
        ],
        default=Role.STUDENT,
    )

    # Additional fields from original codebase that might be needed, keeping them optional
    bio = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    objects = CustomUserManager()

    @property
    def is_administrator(self):
        return self.role == Role.ADMIN

    @property
    def is_club_manager(self):
        return self.role == Role.CLUB_MANAGER

    @property
    def is_student(self):
        return not self.is_administrator and not self.is_club_manager

    def __str__(self):
        return f"{self.email} ({self.first_name} {self.last_name})"


class ClubPortalCredential(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_portal_credentials')
    club = models.ForeignKey('clubs.Club', on_delete=models.CASCADE, related_name='manager_credentials')
    username = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Club Portal Credential'
        verbose_name_plural = 'Club Portal Credentials'

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return f"{self.username} -> {self.club.name}"


class EmailVerificationCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification_code')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        from django.conf import settings
        expiry = getattr(settings, 'VERIFICATION_CODE_EXPIRY', 600)
        return timezone.now() > self.created_at + timedelta(seconds=expiry)

    @classmethod
    def generate_for(cls, user):
        code = str(random.randint(100000, 999999))
        obj, _ = cls.objects.update_or_create(
            user=user,
            defaults={'code': code, 'is_used': False, 'created_at': timezone.now()},
        )
        return code
