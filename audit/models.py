import uuid
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    M7 - Audit trail matching 'Audit Log' in the class diagram.
    """
    class AuditAction(models.TextChoices):
        MEMBER_JOINED = 'MEMBER JOINED', 'Member Joined'
        MEMBER_LEFT = 'MEMBER LEFT', 'Member Left'
        MEMBER_KICKED = 'MEMBER KICKED', 'Member Kicked'
        MEMBER_BANNED = 'MEMBER BANNED', 'Member Banned'
        INVITE_ACCEPTED = 'INVITE ACCEPTED', 'Invite Accepted'
        ROLE_ASSIGNED = 'ROLE ASSIGNED', 'Role Assigned'
        ROLE_CHANGED = 'ROLE CHANGED', 'Role Changed'
        CLUB_UPDATED = 'CLUB UPDATED', 'Club Updated'
        CLUB_SETTING_CHANGED = 'CLUB SETTING CHANGED', 'Club Setting Changed'
        USER_LOGIN = 'USER LOGIN', 'User Login'
        USER_LOGOUT = 'USER LOGOUT', 'User Logout'
        USER_PROFILE_UPDATED = 'USER PROFILE UPDATED', 'User Profile Updated'

    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    metadata = models.JSONField(default=dict, blank=True)
    ip_adress = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    entity_type = models.CharField(max_length=100, blank=True, default='')
    entity_id = models.UUIDField(null=True, blank=True)
    
    # Acteur relation
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        user_str = self.user.username if self.user else 'anonymous'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {user_str} - {self.action}"
