from datetime import timedelta
from decimal import Decimal

from django.test import TestCase

from bookings.serializers import AccommodationSerializer, BookingCreateUpdateSerializer
from budgets.serializers import BudgetSerializer, ExpenseSerializer
from config.test_helpers import TravelFixtureMixin
from destinations.serializers import DestinationDetailSerializer, DestinationListSerializer
from itineraries.serializers import (
    CollaborationSerializer,
    DailyPlanSerializer,
    ItineraryCreateUpdateSerializer,
    ItineraryDetailSerializer,
)
from reviews.serializers import ReviewSerializer


class SerializerTests(TravelFixtureMixin, TestCase):
    def test_destination_list_has_weekly_estimate(self):
        data = DestinationListSerializer(self.destination).data
        self.assertEqual(Decimal(data["estimated_weekly_cost"]), Decimal("875.00"))

    def test_destination_detail_has_activity_count(self):
        data = DestinationDetailSerializer(self.destination).data
        self.assertEqual(data["activity_count"], 1)

    def test_itinerary_rejects_reversed_dates(self):
        serializer = ItineraryCreateUpdateSerializer(
            data={
                "title": "Invalid",
                "destination": self.destination.pk,
                "start_date": self.itinerary.end_date,
                "end_date": self.itinerary.start_date,
                "budget": "100.00",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_itinerary_create_auto_creates_budget(self):
        serializer = ItineraryCreateUpdateSerializer(
            data={
                "title": "Second trip",
                "destination": self.destination.pk,
                "start_date": self.itinerary.start_date,
                "end_date": self.itinerary.end_date,
                "budget": "500.00",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        itinerary = serializer.save(owner=self.user)
        self.assertTrue(hasattr(itinerary, "budget_detail"))

    def test_itinerary_detail_is_nested(self):
        data = ItineraryDetailSerializer(self.itinerary).data
        self.assertEqual(data["destination"]["name"], "Cape Town")
        self.assertEqual(data["owner"]["username"], "traveller")

    def test_daily_plan_serializer_rejects_outside_date(self):
        serializer = DailyPlanSerializer(
            data={
                "day_number": 8,
                "date": self.itinerary.end_date + timedelta(days=1),
                "title": "Late",
            },
            context={"itinerary": self.itinerary},
        )
        self.assertFalse(serializer.is_valid())

    def test_collaboration_accepts_email(self):
        serializer = CollaborationSerializer(data={"email": self.outsider.email, "role": "editor"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["user"], self.outsider)

    def test_accommodation_requires_amenities_list(self):
        serializer = AccommodationSerializer(
            self.accommodation, data={"amenities": "wifi"}, partial=True
        )
        self.assertFalse(serializer.is_valid())

    def test_booking_rejects_two_products(self):
        serializer = BookingCreateUpdateSerializer(
            self.booking,
            data={"accommodation": self.accommodation.pk, "activity": self.activity.pk},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())

    def test_review_rejects_missing_target(self):
        serializer = ReviewSerializer(
            data={
                "rating": 4,
                "title": "Nice",
                "content": "Good visit",
                "visit_date": self.itinerary.start_date,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_expense_updates_actual_spent(self):
        serializer = ExpenseSerializer(
            data={
                "itinerary": self.itinerary.pk,
                "category": "food",
                "description": "Lunch",
                "amount": "25.00",
                "date": self.itinerary.start_date,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.itinerary.refresh_from_db()
        self.assertEqual(self.itinerary.actual_spent, Decimal("25.00"))

    def test_budget_serializer_has_computed_totals(self):
        data = BudgetSerializer(self.budget).data
        self.assertIn("total_budget", data)
        self.assertIn("remaining", data)
