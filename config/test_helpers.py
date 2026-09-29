"""Shared, realistic fixtures for API and domain tests."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from bookings.models import Accommodation, Activity, Booking
from budgets.models import Budget
from destinations.models import Destination
from itineraries.models import Collaboration, Itinerary


class TravelFixtureMixin:
    """Create a reusable travel graph while keeping individual tests focused."""

    def setUp(self):
        super().setUp()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="traveller", email="traveller@example.com", password="StrongPass123!"
        )
        self.collaborator = user_model.objects.create_user(
            username="companion", email="companion@example.com", password="StrongPass123!"
        )
        self.outsider = user_model.objects.create_user(
            username="outsider", email="outsider@example.com", password="StrongPass123!"
        )
        self.destination = Destination.objects.create(
            name="Cape Town",
            country="South Africa",
            description="Coast, culture, and mountains.",
            category=Destination.Category.CITY,
            climate=Destination.Climate.TEMPERATE,
            best_time_to_visit="November to March",
            avg_daily_cost=Decimal("125.00"),
            latitude=Decimal("-33.924900"),
            longitude=Decimal("18.424100"),
        )
        start = timezone.localdate() + timedelta(days=10)
        self.itinerary = Itinerary.objects.create(
            title="Cape escape",
            destination=self.destination,
            owner=self.user,
            start_date=start,
            end_date=start + timedelta(days=4),
            budget=Decimal("2000.00"),
        )
        self.budget = Budget.objects.create(itinerary=self.itinerary)
        self.collaboration = Collaboration.objects.create(
            itinerary=self.itinerary,
            user=self.collaborator,
            role=Collaboration.Role.VIEWER,
        )
        self.accommodation = Accommodation.objects.create(
            name="Harbour Hotel",
            destination=self.destination,
            accommodation_type=Accommodation.Type.HOTEL,
            description="Central hotel",
            price_per_night=Decimal("180.00"),
            max_guests=2,
            amenities=["wifi", "breakfast"],
            address="1 Harbour Road",
            contact_email="stay@example.com",
        )
        self.activity = Activity.objects.create(
            name="Table Mountain walk",
            destination=self.destination,
            category=Activity.Category.OUTDOOR,
            description="Guided walk",
            duration_hours=Decimal("3.0"),
            price=Decimal("45.00"),
            max_participants=12,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            itinerary=self.itinerary,
            activity=self.activity,
            booking_date=start + timedelta(days=1),
            price=Decimal("45.00"),
        )
