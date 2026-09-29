"""Booking inventory and transaction serializers."""
from rest_framework import serializers

from destinations.serializers import DestinationListSerializer
from itineraries.serializers import ItineraryListSerializer

from .models import Accommodation, Activity, Booking


class AccommodationSerializer(serializers.ModelSerializer):
    destination_details = DestinationListSerializer(source="destination", read_only=True)
    amenities_count = serializers.SerializerMethodField()

    class Meta:
        model = Accommodation
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def get_amenities_count(self, obj):
        return len(obj.amenities)

    def validate_amenities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Amenities must be a list.")
        return value


class ActivitySerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def get_average_rating(self, obj):
        return obj.rating


class BookingListSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    booking_type = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "itinerary",
            "accommodation",
            "activity",
            "item_name",
            "booking_type",
            "booking_date",
            "price",
            "status",
            "confirmation_code",
        )

    def get_item_name(self, obj):
        item = obj.accommodation or obj.activity
        return item.name if item else None

    def get_booking_type(self, obj):
        return "accommodation" if obj.accommodation_id else "activity"


class BookingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = (
            "itinerary",
            "accommodation",
            "activity",
            "booking_date",
            "check_in",
            "check_out",
            "guests_count",
            "price",
            "notes",
        )

    def validate(self, attrs):
        accommodation = attrs.get("accommodation", getattr(self.instance, "accommodation", None))
        activity = attrs.get("activity", getattr(self.instance, "activity", None))
        if bool(accommodation) == bool(activity):
            raise serializers.ValidationError(
                "Choose exactly one accommodation or activity."
            )
        itinerary = attrs.get("itinerary", getattr(self.instance, "itinerary", None))
        item = accommodation or activity
        if itinerary and item and item.destination_id != itinerary.destination_id:
            raise serializers.ValidationError("Booked item and itinerary destinations must match.")
        request = self.context.get("request")
        if request and itinerary:
            has_trip_access = itinerary.owner_id == request.user.id
            if not has_trip_access:
                has_trip_access = itinerary.collaborators.filter(id=request.user.id).exists()
            if not has_trip_access:
                raise serializers.ValidationError(
                    {"itinerary": "You cannot book against this itinerary."}
                )
        check_in = attrs.get("check_in", getattr(self.instance, "check_in", None))
        check_out = attrs.get("check_out", getattr(self.instance, "check_out", None))
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError({"check_out": "Check-out must be after check-in."})
        return attrs

    def to_representation(self, instance):
        return BookingDetailSerializer(instance, context=self.context).data


class BookingDetailSerializer(BookingListSerializer):
    itinerary_details = ItineraryListSerializer(source="itinerary", read_only=True)
    accommodation_details = AccommodationSerializer(source="accommodation", read_only=True)
    activity_details = ActivitySerializer(source="activity", read_only=True)

    class Meta:
        model = Booking
        fields = BookingListSerializer.Meta.fields + (
            "itinerary_details",
            "accommodation_details",
            "activity_details",
            "check_in",
            "check_out",
            "guests_count",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("confirmation_code", "created_at", "updated_at")
