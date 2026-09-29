from rest_framework import serializers

from accounts.serializers import UserSummarySerializer

from .models import Review


class ReviewListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "username",
            "target_name",
            "rating",
            "title",
            "helpful_count",
            "created_at",
        )

    def get_target_name(self, obj):
        return obj.target.name


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    target_type = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "user",
            "destination",
            "accommodation",
            "activity",
            "target_type",
            "target_name",
            "rating",
            "title",
            "content",
            "visit_date",
            "images",
            "helpful_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("helpful_count", "created_at", "updated_at")

    def get_target_type(self, obj):
        if obj.destination_id:
            return "destination"
        return "accommodation" if obj.accommodation_id else "activity"

    def get_target_name(self, obj):
        return obj.target.name

    def validate_images(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Images must be a list of URLs.")
        return value

    def validate(self, attrs):
        targets = [
            attrs.get("destination", getattr(self.instance, "destination", None)),
            attrs.get("accommodation", getattr(self.instance, "accommodation", None)),
            attrs.get("activity", getattr(self.instance, "activity", None)),
        ]
        if sum(bool(target) for target in targets) != 1:
            raise serializers.ValidationError(
                "Review exactly one destination, accommodation, or activity."
            )
        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["can_edit"] = bool(
            self.context.get("request")
            and self.context["request"].user.is_authenticated
            and self.context["request"].user.pk == instance.user_id
        )
        return representation


class ReviewCreateUpdateSerializer(ReviewSerializer):
    class Meta:
        model = Review
        fields = (
            "destination",
            "accommodation",
            "activity",
            "rating",
            "title",
            "content",
            "visit_date",
            "images",
        )

    def to_representation(self, instance):
        return ReviewSerializer(instance, context=self.context).data
