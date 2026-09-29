from django.urls import path

from .views import (
    DailyPlanListCreateView,
    ItineraryListCreateView,
    TripCollaborationView,
    generate_trip_report,
)

app_name = "itineraries"

urlpatterns = [
    path("", ItineraryListCreateView.as_view(), name="list-create"),
    path("report/", generate_trip_report, name="trip-report"),
    path("<int:pk>/collaborations/", TripCollaborationView.as_view(), name="collaborations"),
    path("<int:itinerary_pk>/days/", DailyPlanListCreateView.as_view(), name="daily-plans"),
]
