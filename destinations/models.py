"""Travel destination catalogue."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Destination(models.Model):
    class Category(models.TextChoices):
        BEACH = "beach", "Beach"
        CITY = "city", "City"
        MOUNTAIN = "mountain", "Mountain"
        COUNTRYSIDE = "countryside", "Countryside"
        CULTURAL = "cultural", "Cultural"
        ADVENTURE = "adventure", "Adventure"
        RELAXATION = "relaxation", "Relaxation"

    CategoryChoices = Category

    class Climate(models.TextChoices):
        TROPICAL = "tropical", "Tropical"
        DRY = "dry", "Dry"
        TEMPERATE = "temperate", "Temperate"
        CONTINENTAL = "continental", "Continental"
        POLAR = "polar", "Polar"

    ClimateChoices = Climate

    name = models.CharField(
        max_length=200, unique=True, help_text="Public name of the destination."
    )
    country = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    climate = models.CharField(max_length=20, choices=Climate.choices, db_index=True)
    best_time_to_visit = models.CharField(max_length=120, blank=True)
    avg_daily_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Estimated average cost per traveller per day.",
    )
    image = models.ImageField(upload_to="destinations/", null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["country", "category"]),
            models.Index(fields=["climate", "is_active"]),
        ]
        verbose_name = "destination"
        verbose_name_plural = "destinations"

    def __str__(self):
        return f"{self.name}, {self.country}"

    def estimated_cost(self, days):
        return self.avg_daily_cost * days

    @property
    def average_rating(self):
        return self.reviews.aggregate(models.Avg("rating"))["rating__avg"] or 0
