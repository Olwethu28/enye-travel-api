"""Budget allocation and expense endpoints."""
from django.db.models import Prefetch, Q, Sum
from rest_framework import filters, permissions, viewsets

from itineraries.permissions import CanEditItinerary, IsTripOwnerOrCollaborator

from .models import Budget, Expense
from .serializers import BudgetSerializer, ExpenseSerializer


class BudgetViewSet(viewsets.ModelViewSet):
    """Manage category allocations for accessible itineraries."""

    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated, IsTripOwnerOrCollaborator, CanEditItinerary]

    def get_queryset(self):
        user = self.request.user
        return (
            Budget.objects.filter(itinerary__owner=user)
            | Budget.objects.filter(itinerary__collaborators=user)
        ).select_related("itinerary", "itinerary__destination").prefetch_related(
            Prefetch("itinerary__expenses", queryset=Expense.objects.order_by("-date"))
        ).annotate(expense_total=Sum("itinerary__expenses__amount")).distinct()


class ExpenseViewSet(viewsets.ModelViewSet):
    """Record itemized costs against a trip."""

    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, CanEditItinerary]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "notes"]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        user = self.request.user
        return Expense.objects.filter(
            Q(itinerary__owner=user) | Q(itinerary__collaborators=user)
        ).select_related("itinerary", "itinerary__owner").distinct()

    def perform_destroy(self, instance):
        itinerary = instance.itinerary
        super().perform_destroy(instance)
        total = itinerary.expenses.aggregate(total=Sum("amount"))["total"] or 0
        itinerary.actual_spent = total
        itinerary.save(update_fields=["actual_spent", "updated_at"])
