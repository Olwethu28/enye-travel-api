"""Serializers for registration and traveller profiles."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "display_name", "profile_picture")

    def get_display_name(self, obj):
        return obj.display_name


class UserProfileSerializer(UserSummarySerializer):
    class Meta(UserSummarySerializer.Meta):
        fields = UserSummarySerializer.Meta.fields + (
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
            "bio",
            "travel_preferences",
            "role",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("role", "created_at", "updated_at")

    def validate_travel_preferences(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Travel preferences must be an object.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    tokens = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
            "tokens",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def get_tokens(self, obj):
        refresh = RefreshToken.for_user(obj)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}
