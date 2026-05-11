import uuid
from django.db import models
from django.conf import settings


class Request(models.Model):
    """
    Represents a request matching the 'Request' class in the class diagram.
    """
    class RequestType(models.TextChoices):
        CLUB_CREATION = 'CLUB CREATION', 'Club Creation'
        CLAIM = 'CLAIM', 'Claim'
        ADMINISTRATIVE = 'ADMINISTRATIVE', 'Administrative'
        LOGISTICS = 'LOGISTICS', 'Logistics'

    class RequestStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        TREATED = 'TREATED', 'Treated'
        REJECTED = 'REJECTED', 'Rejected'
        IN_PROGRESS = 'IN PROGRESS', 'In Progress'

    request_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_type = models.CharField(max_length=50, choices=RequestType.choices)
    status = models.CharField(max_length=50, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Implicit relationship based on logical context: request made by user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests', null=True, blank=True)
    treated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='treated_requests',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Request'
        verbose_name_plural = 'Requests'

    def __str__(self):
        return f"{self.title} ({self.status})"
