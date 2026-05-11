import uuid
from django.conf import settings
from django.db import models


class Club(models.Model):
    """
    Represents a university club matching the 'Club' entity in the class diagram.
    """
    club_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')
    logo = models.ImageField(upload_to='club_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Keeping category and updated_at from previous model just in case, optional
    category = models.CharField(max_length=100, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Club'
        verbose_name_plural = 'Clubs'

    def __str__(self):
        return self.name


class ClubMembership(models.Model):
    """
    Represents a user's membership in a club matching 'Club MemberShip' in the class diagram.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_memberships',
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    internal_role = models.CharField(max_length=50, default='member')
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('approved', 'Approved'), ('banned', 'Banned'), ('pending', 'Pending')],
        default='active',
    )

    class Meta:
        unique_together = ('user', 'club')
        ordering = ['-joined_at']
        verbose_name = 'Club Membership'
        verbose_name_plural = 'Club Memberships'

    def __str__(self):
        return f"{self.user.username} -> {self.club.name}"
