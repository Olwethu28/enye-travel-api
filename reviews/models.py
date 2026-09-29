"""Reviews for destinations and bookable travel products."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from bookings.models import Accommodation, Activity
from destinations.models import Destination


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True
    )
    accommodation = models.ForeignKey(
        Accommodation, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True
    )
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Whole-number rating from one to five.",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    visit_date = models.DateField()
    images = models.JSONField(
        default=list, blank=True, help_text="List of hosted review image URLs."
    )
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["destination", "rating"]),
            models.Index(fields=["accommodation", "rating"]),
            models.Index(fields=["activity", "rating"]),
            models.Index(fields=["user", "created_at"]),
        ]
        verbose_name = "review"

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    def clean(self):
        targets = [self.destination_id, self.accommodation_id, self.activity_id]
        if sum(target is not None for target in targets) != 1:
            raise ValidationError("Review must be for exactly one item.")

    @property
    def target(self):
        return self.destination or self.accommodation or self.activity

    def mark_helpful(self):
        self.helpful_count = models.F("helpful_count") + 1
        self.save(update_fields=["helpful_count", "updated_at"])
        self.refresh_from_db(fields=["helpful_count"])
