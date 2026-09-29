from django.db import transaction
from django.db.models import F, Sum
from rest_framework import serializers

from itineraries.models import Itinerary

from .models import Budget, Expense


class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        itinerary = attrs.get("itinerary", getattr(self.instance, "itinerary", None))
        date = attrs.get("date", getattr(self.instance, "date", None))
        if itinerary and date and not itinerary.start_date <= date <= itinerary.end_date:
            raise serializers.ValidationError({"date": "Expense date must fall within the trip."})
        request = self.context.get("request")
        if request and itinerary and itinerary.owner_id != request.user.id:
            editable = itinerary.collaborations.filter(
                user=request.user, role__in=("editor", "admin")
            ).exists()
            if not editable:
                raise serializers.ValidationError("You cannot add expenses to this itinerary.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        expense = super().create(validated_data)
        Itinerary.objects.filter(pk=expense.itinerary_id).update(
            actual_spent=F("actual_spent") + expense.amount
        )
        return expense

    @transaction.atomic
    def update(self, instance, validated_data):
        old_itinerary_id = instance.itinerary_id
        result = super().update(instance, validated_data)
        for itinerary_id in {old_itinerary_id, result.itinerary_id}:
            total = Expense.objects.filter(itinerary_id=itinerary_id).aggregate(
                total=Sum("amount")
            )["total"] or 0
            Itinerary.objects.filter(pk=itinerary_id).update(actual_spent=total)
        return result


class BudgetSerializer(serializers.ModelSerializer):
    total_budget = serializers.ReadOnlyField()
    total_spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    expenses = ExpenseSerializer(source="itinerary.expenses", many=True, read_only=True)

    class Meta:
        model = Budget
        fields = (
            "id",
            "itinerary",
            "accommodation_budget",
            "activities_budget",
            "food_budget",
            "transport_budget",
            "shopping_budget",
            "miscellaneous_budget",
            "total_budget",
            "total_spent",
            "remaining",
            "expenses",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_total_spent(self, obj):
        return getattr(obj, "expense_total", None) or obj.itinerary.actual_spent

    def get_remaining(self, obj):
        return obj.total_budget - self.get_total_spent(obj)

    def validate(self, attrs):
        budget_fields = [field for field in attrs if field.endswith("_budget")]
        if any(attrs[field] < 0 for field in budget_fields):
            raise serializers.ValidationError("Budget allocations cannot be negative.")
        itinerary = attrs.get("itinerary", getattr(self.instance, "itinerary", None))
        request = self.context.get("request")
        if request and itinerary:
            can_edit = itinerary.owner_id == request.user.id
            if not can_edit:
                can_edit = itinerary.collaborations.filter(
                    user=request.user, role__in=("editor", "admin")
                ).exists()
            if not can_edit:
                raise serializers.ValidationError("You cannot manage this trip budget.")
        return attrs
