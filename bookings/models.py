"""Bookable accommodation and activity inventory."""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from destinations.models import Destination
from itineraries.models import Itinerary


class Accommodation(models.Model):
    class Type(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        HOSTEL = "hostel", "Hostel"
        RENTAL = "rental", "Vacation Rental"
        RESORT = "resort", "Resort"
        BNB = "bnb", "B&B"

    TypeChoices = Type

    name = models.CharField(max_length=200)
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="accommodations"
    )
    accommodation_type = models.CharField(max_length=10, choices=Type.choices)
    description = models.TextField()
    price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    max_guests = models.PositiveIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True, help_text="List of included amenities.")
    address = models.CharField(max_length=300)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    image = models.ImageField(upload_to="accommodations/", null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["destination", "accommodation_type"])]
        verbose_name = "accommodation"

    def __str__(self):
        return f"{self.name} ({self.get_accommodation_type_display()})"

    def cost_for_nights(self, nights):
        return self.price_per_night * nights


class Activity(models.Model):
    class Category(models.TextChoices):
        TOUR = "tour", "Tour"
        ATTRACTION = "attraction", "Attraction"
        DINING = "dining", "Dining"
        SHOPPING = "shopping", "Shopping"
        ENTERTAINMENT = "entertainment", "Entertainment"
        OUTDOOR = "outdoor", "Outdoor"

    CategoryChoices = Category

    name = models.CharField(max_length=200)
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="activities"
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    requirements = models.TextField(blank=True)
    image = models.ImageField(upload_to="activities/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["destination", "category"])]
        verbose_name = "activity"
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.name} - {self.destination.name}"

    @property
    def rating(self):
        annotated_rating = getattr(self, "average_rating_value", None)
        if annotated_rating is not None:
            return annotated_rating
        cache = getattr(self, "_prefetched_objects_cache", {})
        if "reviews" in cache:
            ratings = [review.rating for review in cache["reviews"]]
            return sum(ratings) / len(ratings) if ratings else 0
        return self.reviews.aggregate(models.Avg("rating"))["rating__avg"] or 0


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    StatusChoices = Status

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings"
    )
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="bookings")
    accommodation = models.ForeignKey(
        Accommodation, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    activity = models.ForeignKey(
        Activity, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    booking_date = models.DateField(help_text="Date on which the booked service will be used.")
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    guests_count = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    confirmation_code = models.CharField(max_length=50, blank=True, unique=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["itinerary", "booking_date"]),
        ]
        verbose_name = "booking"

    def __str__(self):
        item = self.accommodation or self.activity
        return f"Booking: {item}" if item else f"Booking #{self.pk}"

    def clean(self):
        if bool(self.accommodation_id) == bool(self.activity_id):
            raise ValidationError("Booking must have exactly one accommodation or activity.")
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError({"check_out": "Check-out must be after check-in."})
        if self.itinerary_id:
            if self.accommodation_id:
                destination_id = self.accommodation.destination_id
            else:
                destination_id = self.activity.destination_id
            if destination_id != self.itinerary.destination_id:
                raise ValidationError("The booked item must belong to the itinerary destination.")

    def confirm(self):
        if not self.confirmation_code:
            self.confirmation_code = uuid.uuid4().hex[:12].upper()
        self.status = self.Status.CONFIRMED
        self.save(update_fields=["status", "confirmation_code", "updated_at"])

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])
