"""Collaborative trip itinerary models."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from destinations.models import Destination


class Itinerary(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        BOOKED = "booked", "Booked"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    StatusChoices = Status

    title = models.CharField(max_length=200, help_text="A memorable name for the trip.")
    description = models.TextField(blank=True)
    destination = models.ForeignKey(
        Destination, on_delete=models.PROTECT, related_name="itineraries"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_itineraries"
    )
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Collaboration",
        related_name="shared_itineraries",
        blank=True,
    )
    start_date = models.DateField(help_text="First calendar day of the trip.")
    end_date = models.DateField(help_text="Last calendar day of the trip.")
    budget = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    actual_spent = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    is_public = models.BooleanField(default=False)
    itinerary_pdf = models.FileField(upload_to="itineraries/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["destination", "is_public"]),
        ]
        verbose_name = "itinerary"
        verbose_name_plural = "itineraries"

    def __str__(self):
        return f"{self.title} - {self.destination.name}"

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def budget_remaining(self):
        return self.budget - self.actual_spent

    def add_collaborator(self, user, role="viewer"):
        collaboration, _ = Collaboration.objects.update_or_create(
            itinerary=self, user=user, defaults={"role": role}
        )
        return collaboration


class Collaboration(models.Model):
    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        EDITOR = "editor", "Editor"
        ADMIN = "admin", "Admin"

    RoleChoices = Role

    itinerary = models.ForeignKey(
        Itinerary, on_delete=models.CASCADE, related_name="collaborations"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collaborations"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    invited_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-invited_at"]
        unique_together = ("itinerary", "user")
        indexes = [models.Index(fields=["itinerary", "role"])]
        verbose_name = "trip collaboration"

    def __str__(self):
        return f"{self.user.username} - {self.itinerary.title} ({self.role})"

    def clean(self):
        if self.itinerary_id and self.user_id and self.itinerary.owner_id == self.user_id:
            raise ValidationError("The itinerary owner cannot also be a collaborator.")


class DailyPlan(models.Model):
    itinerary = models.ForeignKey(
        Itinerary, on_delete=models.CASCADE, related_name="daily_plans"
    )
    activities = models.ManyToManyField(
        "bookings.Activity", related_name="daily_plans", blank=True
    )
    day_number = models.PositiveIntegerField(help_text="One-based day number within the trip.")
    date = models.DateField()
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_number"]
        unique_together = ("itinerary", "day_number")
        indexes = [models.Index(fields=["itinerary", "date"])]
        verbose_name = "daily plan"

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"

    def clean(self):
        if self.day_number < 1:
            raise ValidationError({"day_number": "Day number must be at least one."})
        if self.itinerary_id and self.date:
            if not self.itinerary.start_date <= self.date <= self.itinerary.end_date:
                raise ValidationError({"date": "Daily plan date must fall within the trip."})
