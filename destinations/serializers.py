from rest_framework import serializers

from .models import Destination


class DestinationListSerializer(serializers.ModelSerializer):
    estimated_weekly_cost = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = (
            "id",
            "name",
            "country",
            "category",
            "climate",
            "avg_daily_cost",
            "image",
            "estimated_weekly_cost",
        )

    def get_estimated_weekly_cost(self, obj):
        return obj.estimated_cost(7)


class DestinationDetailSerializer(DestinationListSerializer):
    activity_count = serializers.SerializerMethodField()

    class Meta(DestinationListSerializer.Meta):
        fields = DestinationListSerializer.Meta.fields + (
            "description",
            "best_time_to_visit",
            "latitude",
            "longitude",
            "is_active",
            "activity_count",
            "created_at",
            "updated_at",
        )

    def get_activity_count(self, obj):
        return getattr(obj, "activity_count", obj.activities.count())
