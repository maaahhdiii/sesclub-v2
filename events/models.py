from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from clubs.models import Club


class Event(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
    ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    date = models.DateTimeField(default=timezone.now)
    capacity = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['-date']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def __str__(self):
        return self.title


class EventRegistration(models.Model):
    """
    Represents a student's registration for an event matching 'EventRegistration' in the class diagram.
    """
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
    registered_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'event')
        ordering = ['-registered_at']
        verbose_name = 'Event Registration'
        verbose_name_plural = 'Event Registrations'

    def __str__(self):
        return f"{self.user.username} -> {self.event.title}"


class Review(models.Model):
    """
    Represents a review matching 'Review' in the class diagram.
    Assumed to be on an Event based on structural context.
    """
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, default='')
    
    # Relationships derived from '1..* avoir 1* Gérer' and '1* Faire'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_made')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f"Review {self.rating}/5 by {self.user.username}"


class GoogleCalendarCredentials(models.Model):
    """Stores Google Calendar OAuth tokens for a user."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='google_calendar')
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=30, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    calendar_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"GoogleCalendarCredentials({self.user_id})"
