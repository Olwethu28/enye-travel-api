from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from bookings.models import Booking
from budgets.models import Expense
from config.test_helpers import TravelFixtureMixin
from itineraries.models import Collaboration, DailyPlan
from reviews.models import Review


class DomainModelTests(TravelFixtureMixin, TestCase):
    def test_user_display_name_falls_back_to_username(self):
        self.assertEqual(self.user.display_name, "traveller")

    def test_destination_string_and_estimated_cost(self):
        self.assertEqual(str(self.destination), "Cape Town, South Africa")
        self.assertEqual(self.destination.estimated_cost(2), Decimal("250.00"))

    def test_destination_coordinates_are_validated(self):
        self.destination.latitude = 100
        with self.assertRaises(ValidationError):
            self.destination.full_clean()

    def test_itinerary_computed_properties(self):
        self.itinerary.actual_spent = Decimal("100.00")
        self.assertEqual(self.itinerary.duration_days, 5)
        self.assertEqual(self.itinerary.budget_remaining, Decimal("1900.00"))

    def test_itinerary_rejects_reversed_dates(self):
        self.itinerary.end_date = self.itinerary.start_date - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.itinerary.full_clean()

    def test_collaboration_rejects_owner(self):
        collaboration = Collaboration(itinerary=self.itinerary, user=self.user)
        with self.assertRaises(ValidationError):
            collaboration.full_clean()

    def test_daily_plan_must_be_inside_trip(self):
        plan = DailyPlan(
            itinerary=self.itinerary,
            day_number=6,
            date=self.itinerary.end_date + timedelta(days=1),
            title="Too late",
        )
        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_accommodation_cost_for_nights(self):
        self.assertEqual(self.accommodation.cost_for_nights(3), Decimal("540.00"))

    def test_booking_requires_exactly_one_product(self):
        booking = Booking(
            user=self.user,
            itinerary=self.itinerary,
            booking_date=self.itinerary.start_date,
            price=10,
        )
        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_confirmation_generates_code(self):
        self.booking.confirm()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(len(self.booking.confirmation_code), 12)

    def test_review_requires_exactly_one_target(self):
        review = Review(
            user=self.user,
            destination=self.destination,
            activity=self.activity,
            rating=5,
            title="Excellent",
            content="Loved it",
            visit_date=self.itinerary.start_date,
        )
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_budget_total(self):
        self.budget.accommodation_budget = Decimal("500.00")
        self.budget.food_budget = Decimal("250.00")
        self.assertEqual(self.budget.total_budget, Decimal("750.00"))

    def test_expense_date_must_be_inside_trip(self):
        expense = Expense(
            itinerary=self.itinerary,
            category=Expense.Category.FOOD,
            description="Early meal",
            amount=20,
            date=self.itinerary.start_date - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()
