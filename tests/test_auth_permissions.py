from rest_framework import status
from rest_framework.test import APITestCase

from config.test_helpers import TravelFixtureMixin


class AuthenticationAndPermissionTests(TravelFixtureMixin, APITestCase):
    def test_registration_returns_tokens(self):
        response = self.client.post(
            "/api/v1/accounts/register/",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "DifferentStrong123!",
                "password_confirm": "DifferentStrong123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("access", response.data["tokens"])

    def test_jwt_login(self):
        response = self.client.post(
            "/api/v1/accounts/login/",
            {"username": self.user.username, "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)

    def test_profile_returns_authenticated_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/accounts/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_preferences_can_be_patched(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            "/api/v1/accounts/preferences/",
            {"travel_preferences": {"climate": "temperate"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["travel_preferences"]["climate"], "temperate")

    def test_viewer_can_read_shared_itinerary(self):
        self.client.force_authenticate(self.collaborator)
        response = self.client.get(f"/api/v1/itineraries/{self.itinerary.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_edit_shared_itinerary(self):
        self.client.force_authenticate(self.collaborator)
        response = self.client.patch(
            f"/api/v1/itineraries/{self.itinerary.pk}/", {"title": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_cannot_read_private_itinerary(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(f"/api/v1/itineraries/{self.itinerary.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_access_booking(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(f"/api/v1/bookings/{self.booking.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_viewer_cannot_add_daily_plan(self):
        self.client.force_authenticate(self.collaborator)
        response = self.client.post(
            f"/api/v1/trips/{self.itinerary.pk}/days/",
            {"day_number": 1, "date": self.itinerary.start_date, "title": "No access"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
