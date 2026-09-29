from django.urls import path

from .views import BookingDetailView

app_name = "bookings"

urlpatterns = [path("detail/<int:pk>/", BookingDetailView.as_view(), name="booking-detail")]
