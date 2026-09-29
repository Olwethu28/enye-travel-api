from rest_framework import status
from rest_framework.test import APITestCase

from config.test_helpers import TravelFixtureMixin
from itineraries.models import Collaboration, DailyPlan, Itinerary
from reviews.models import Review


class ApiViewTests(TravelFixtureMixin, APITestCase):
    def test_destination_list_is_public_and_paginated(self):
        response = self.client.get("/api/v1/destinations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_trip_search_get(self):
        response = self.client.get("/api/v1/destinations/search/?q=Cape")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_trip_search_post(self):
        response = self.client.post(
            "/api/v1/destinations/search/", {"category": "city"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_itinerary_list_requires_authentication(self):
        response = self.client.get("/api/v1/itineraries/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_create_itinerary(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/itineraries/",
            {
                "title": "Garden Route",
                "destination": self.destination.pk,
                "start_date": self.itinerary.start_date,
                "end_date": self.itinerary.end_date,
                "budget": "1000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Itinerary.objects.filter(title="Garden Route", owner=self.user).exists())

    def test_owner_can_duplicate_itinerary(self):
        DailyPlan.objects.create(
            itinerary=self.itinerary,
            day_number=1,
            date=self.itinerary.start_date,
            title="Arrival",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/v1/itineraries/{self.itinerary.pk}/duplicate/", {}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Itinerary.objects.filter(owner=self.user).count(), 2)

    def test_upcoming_trips_action(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/itineraries/upcoming_trips/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_nested_daily_plan_create(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/v1/trips/{self.itinerary.pk}/days/",
            {
                "day_number": 1,
                "date": self.itinerary.start_date,
                "title": "Arrival day",
                "activities": [self.activity.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_owner_can_share_trip_by_email(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/v1/itineraries/{self.itinerary.pk}/share_with_user/",
            {"email": self.outsider.email, "role": "editor"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            Collaboration.objects.filter(itinerary=self.itinerary, user=self.outsider).exists()
        )

    def test_booking_list_only_contains_user_bookings(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_booking_can_be_confirmed(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(f"/api/v1/bookings/{self.booking.pk}/confirm/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "confirmed")
        self.assertTrue(response.data["confirmation_code"])

    def test_review_creation_assigns_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/reviews/",
            {
                "destination": self.destination.pk,
                "rating": 5,
                "title": "Wonderful",
                "content": "A memorable city",
                "visit_date": self.itinerary.start_date,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Review.objects.get().user, self.user)

    def test_helpful_action_uses_atomic_increment(self):
        review = Review.objects.create(
            user=self.user,
            destination=self.destination,
            rating=5,
            title="Great",
            content="Great trip",
            visit_date=self.itinerary.start_date,
        )
        self.client.force_authenticate(self.collaborator)
        response = self.client.post(f"/api/v1/reviews/{review.pk}/helpful/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["helpful_count"], 1)

    def test_expense_create_updates_itinerary(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/expenses/",
            {
                "itinerary": self.itinerary.pk,
                "category": "food",
                "description": "Dinner",
                "amount": "40.00",
                "date": self.itinerary.start_date,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.itinerary.refresh_from_db()
        self.assertEqual(str(self.itinerary.actual_spent), "40.00")

    def test_report_returns_aggregates(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/trips/report/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_trips"], 1)

    def test_analytics_destination_preferences(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/analytics/destination_preferences/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["destination__country"], "South Africa")

    def test_schema_and_docs_are_accessible(self):
        schema = self.client.get("/api/v1/schema/")
        swagger = self.client.get("/api/v1/docs/swagger/")
        redoc = self.client.get("/api/v1/docs/redoc/")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(swagger.status_code, 200)
        self.assertEqual(redoc.status_code, 200)
