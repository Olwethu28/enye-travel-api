"""Serializers for itineraries, collaborations, and day plans."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import UserSummarySerializer
from destinations.models import Destination
from destinations.serializers import DestinationListSerializer

from .models import Collaboration, DailyPlan, Itinerary

User = get_user_model()


class CollaborationSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(source="user", read_only=True)
    email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = Collaboration
        fields = ("id", "user", "user_details", "email", "role", "invited_at", "updated_at")
        read_only_fields = ("invited_at", "updated_at")
        extra_kwargs = {"user": {"required": False}}

    def validate(self, attrs):
        email = attrs.pop("email", None)
        if email:
            try:
                attrs["user"] = User.objects.get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise serializers.ValidationError({"email": "No user has this email."}) from exc
        if not attrs.get("user") and not getattr(self.instance, "user_id", None):
            raise serializers.ValidationError({"user": "Choose a user or supply an email."})
        return attrs


class DailyPlanSerializer(serializers.ModelSerializer):
    activities_count = serializers.SerializerMethodField()
    activity_details = serializers.SerializerMethodField()

    class Meta:
        model = DailyPlan
        fields = (
            "id",
            "itinerary",
            "day_number",
            "date",
            "title",
            "notes",
            "activities",
            "activity_details",
            "activities_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("itinerary", "created_at", "updated_at")

    def get_activities_count(self, obj):
        return len(obj._prefetched_objects_cache.get("activities", [])) if hasattr(
            obj, "_prefetched_objects_cache"
        ) and "activities" in obj._prefetched_objects_cache else obj.activities.count()

    def get_activity_details(self, obj):
        from bookings.serializers import ActivitySerializer

        return ActivitySerializer(obj.activities.all(), many=True, context=self.context).data

    def validate(self, attrs):
        itinerary = self.context.get("itinerary") or getattr(self.instance, "itinerary", None)
        date = attrs.get("date", getattr(self.instance, "date", None))
        if itinerary and date and not itinerary.start_date <= date <= itinerary.end_date:
            raise serializers.ValidationError({"date": "Date must fall within the itinerary."})
        activities = attrs.get("activities")
        if itinerary and activities:
            invalid = [
                item.pk
                for item in activities
                if item.destination_id != itinerary.destination_id
            ]
            if invalid:
                raise serializers.ValidationError(
                    {"activities": "Activities must match the itinerary destination."}
                )
        return attrs


class ItineraryListSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    duration_days = serializers.ReadOnlyField()
    budget_remaining = serializers.ReadOnlyField()
    collaborators_count = serializers.SerializerMethodField()

    class Meta:
        model = Itinerary
        fields = (
            "id",
            "title",
            "destination",
            "destination_name",
            "owner",
            "owner_username",
            "start_date",
            "end_date",
            "duration_days",
            "budget",
            "actual_spent",
            "budget_remaining",
            "status",
            "is_public",
            "collaborators_count",
        )
        read_only_fields = ("id", "owner", "actual_spent")

    def get_collaborators_count(self, obj):
        return getattr(obj, "collaborators_count", obj.collaborations.count())


class ItineraryCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Itinerary
        fields = (
            "title",
            "description",
            "destination",
            "start_date",
            "end_date",
            "budget",
            "status",
            "is_public",
            "itinerary_pdf",
        )

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than zero.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs

    def create(self, validated_data):
        itinerary = super().create(validated_data)
        from budgets.models import Budget

        Budget.objects.get_or_create(itinerary=itinerary)
        return itinerary

    def to_representation(self, instance):
        return ItineraryDetailSerializer(instance, context=self.context).data


class ItineraryDetailSerializer(ItineraryListSerializer):
    destination = DestinationListSerializer(read_only=True)
    destination_id = serializers.PrimaryKeyRelatedField(
        source="destination", queryset=Destination.objects.filter(is_active=True), write_only=True
    )
    owner = UserSummarySerializer(read_only=True)
    daily_plans = DailyPlanSerializer(many=True, read_only=True)
    collaborations = CollaborationSerializer(many=True, read_only=True)
    bookings_count = serializers.SerializerMethodField()

    class Meta:
        model = Itinerary
        fields = (
            "id",
            "title",
            "description",
            "destination",
            "destination_id",
            "owner",
            "owner_username",
            "destination_name",
            "start_date",
            "end_date",
            "duration_days",
            "budget",
            "actual_spent",
            "budget_remaining",
            "status",
            "is_public",
            "itinerary_pdf",
            "daily_plans",
            "collaborations",
            "collaborators_count",
            "bookings_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "actual_spent",
            "created_at",
            "updated_at",
        )

    def get_bookings_count(self, obj):
        return getattr(obj, "bookings_count", obj.bookings.count())

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs

    def create(self, validated_data):
        itinerary = super().create(validated_data)
        from budgets.models import Budget

        Budget.objects.get_or_create(itinerary=itinerary)
        return itinerary
