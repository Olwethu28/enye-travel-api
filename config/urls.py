"""Versioned API routes and interactive documentation."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from bookings.views import AccommodationViewSet, ActivityViewSet, BookingViewSet
from budgets.views import BudgetViewSet, ExpenseViewSet
from destinations.views import DestinationViewSet
from itineraries.views import ItineraryViewSet, TripAnalyticsViewSet
from reviews.views import ReviewViewSet

router = DefaultRouter()
router.register("destinations", DestinationViewSet, basename="destination")
router.register("itineraries", ItineraryViewSet, basename="itinerary")
router.register("accommodations", AccommodationViewSet, basename="accommodation")
router.register("activities", ActivityViewSet, basename="activity")
router.register("bookings", BookingViewSet, basename="booking")
router.register("reviews", ReviewViewSet, basename="review")
router.register("budgets", BudgetViewSet, basename="budget")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("analytics", TripAnalyticsViewSet, basename="analytics")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("accounts.urls", namespace="accounts")),
    path("api/v1/destinations/", include("destinations.urls", namespace="destinations")),
    path("api/v1/trips/", include("itineraries.urls", namespace="itineraries")),
    path("api/v1/booking-tools/", include("bookings.urls", namespace="bookings")),
    path("api/v1/review-tools/", include("reviews.urls", namespace="reviews")),
    path("api/v1/budget-tools/", include("budgets.urls", namespace="budgets")),
    path("api/v1/", include(router.urls)),
    path("api/v1/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
