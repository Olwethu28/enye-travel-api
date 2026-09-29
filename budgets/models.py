"""Per-itinerary budget allocations and actual expenses."""
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from itineraries.models import Itinerary


class Budget(models.Model):
    itinerary = models.OneToOneField(
        Itinerary, on_delete=models.CASCADE, related_name="budget_detail"
    )
    accommodation_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activities_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shopping_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    miscellaneous_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["updated_at"])]
        verbose_name = "trip budget"

    def __str__(self):
        return f"Budget for {self.itinerary.title}"

    def clean(self):
        values = (
            self.accommodation_budget,
            self.activities_budget,
            self.food_budget,
            self.transport_budget,
            self.shopping_budget,
            self.miscellaneous_budget,
        )
        if any(value < 0 for value in values):
            raise ValidationError("Budget allocations cannot be negative.")

    @property
    def total_budget(self):
        return sum(
            (
                self.accommodation_budget,
                self.activities_budget,
                self.food_budget,
                self.transport_budget,
                self.shopping_budget,
                self.miscellaneous_budget,
            )
        )


class Expense(models.Model):
    class Category(models.TextChoices):
        ACCOMMODATION = "accommodation", "Accommodation"
        ACTIVITIES = "activities", "Activities"
        FOOD = "food", "Food"
        TRANSPORT = "transport", "Transport"
        SHOPPING = "shopping", "Shopping"
        MISCELLANEOUS = "miscellaneous", "Miscellaneous"

    CategoryChoices = Category

    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Expense amount in the itinerary's working currency.",
    )
    date = models.DateField()
    receipt = models.ImageField(upload_to="receipts/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["itinerary", "category", "date"])]
        verbose_name = "trip expense"

    def __str__(self):
        return f"{self.description} - ${self.amount}"

    def clean(self):
        if self.itinerary_id and self.date:
            if not self.itinerary.start_date <= self.date <= self.itinerary.end_date:
                raise ValidationError({"date": "Expense date must fall within the itinerary."})
