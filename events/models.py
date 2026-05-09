import uuid
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from clubs.models import Club


class Event(models.Model):
    """
    Represents an event matching 'Event' in the class diagram.
    """
    class EventStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'
        IN_PROGRESS = 'in_progress', 'In Progress'

    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    location_detail = models.CharField(max_length=300, blank=True, default='')
    start_time = models.DateTimeField()
    participant_number = models.PositiveIntegerField(default=0)
    event_status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.ACTIVE,
    )
    
    # Keeping relationship to club as it's structurally essential
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='events', null=True, blank=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def __str__(self):
        return self.title


class EventRegistration(models.Model):
    """
    Represents a student's registration for an event matching 'EventRegistration' in the class diagram.
    """
    registration_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations',
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations',
    )
    registred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        ordering = ['-registred_at']
        verbose_name = 'Event Registration'
        verbose_name_plural = 'Event Registrations'

    def __str__(self):
        return f"{self.user.username} -> {self.event.title}"


class Review(models.Model):
    """
    Represents a review matching 'Review' in the class diagram.
    Assumed to be on an Event based on structural context.
    """
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, default='')
    
    # Relationships derived from '1..* avoir 1* Gérer' and '1* Faire'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_made')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f"Review {self.rating}/5 by {self.user.username}"
