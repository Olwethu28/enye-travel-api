"""Bookable inventory and traveller booking endpoints."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import BookingFilter
from .models import Accommodation, Activity, Booking
from .permissions import IsBookingOwner
from .serializers import (
    AccommodationSerializer,
    ActivitySerializer,
    BookingCreateUpdateSerializer,
    BookingDetailSerializer,
    BookingListSerializer,
)


class AccommodationViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse available accommodation inventory."""

    serializer_class = AccommodationSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["destination", "accommodation_type", "is_available"]
    search_fields = ["name", "description", "address", "amenities"]
    ordering_fields = ["name", "price_per_night", "max_guests"]

    def get_queryset(self):
        return Accommodation.objects.select_related("destination").filter(is_available=True)


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse active activities and experiences."""

    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["destination", "category", "is_active"]
    search_fields = ["name", "description", "requirements"]
    ordering_fields = ["name", "price", "duration_hours"]

    def get_queryset(self):
        return Activity.objects.select_related("destination").prefetch_related("reviews").filter(
            is_active=True, is_available=True
        )


class BookingViewSet(viewsets.ModelViewSet):
    """Create and manage bookings belonging to the authenticated traveller."""

    permission_classes = [permissions.IsAuthenticated, IsBookingOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookingFilter
    search_fields = ["confirmation_code", "notes", "accommodation__name", "activity__name"]
    ordering_fields = ["booking_date", "price", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            "user",
            "itinerary",
            "itinerary__destination",
            "accommodation",
            "accommodation__destination",
            "activity",
            "activity__destination",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return BookingListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return BookingCreateUpdateSerializer
        return BookingDetailSerializer

    def perform_create(self, serializer):
        itinerary = serializer.validated_data["itinerary"]
        allowed = itinerary.owner_id == self.request.user.id or itinerary.collaborators.filter(
            id=self.request.user.id
        ).exists()
        if not allowed:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You cannot book against this itinerary.")
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        if booking.status == Booking.Status.CANCELLED:
            return Response({"detail": "A cancelled booking cannot be confirmed."}, status=400)
        booking.confirm()
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status == Booking.Status.COMPLETED:
            return Response({"detail": "A completed booking cannot be cancelled."}, status=400)
        booking.cancel()
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Generic-view endpoint for one traveller-owned booking."""

    permission_classes = [permissions.IsAuthenticated, IsBookingOwner]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            "itinerary", "itinerary__destination", "accommodation", "activity"
        )

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return BookingCreateUpdateSerializer
        return BookingDetailSerializer
