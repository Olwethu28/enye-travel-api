"""Read-only destination discovery endpoints."""
from django.db.models import Avg, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .filters import DestinationFilter
from .models import Destination
from .serializers import DestinationDetailSerializer, DestinationListSerializer


class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse active destinations and destination recommendations."""

    permission_classes = [permissions.AllowAny]
    filterset_class = DestinationFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "country", "description"]
    ordering_fields = ["name", "avg_daily_cost", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Destination.objects.filter(is_active=True).annotate(
            activity_count=Count("activities", distinct=True)
        )

    def get_serializer_class(self):
        if self.action == "list":
            return DestinationListSerializer
        return DestinationDetailSerializer

    @action(detail=True, methods=["get"])
    def popular_activities(self, request, pk=None):
        """Return the highest-rated activities for a destination."""
        from bookings.serializers import ActivitySerializer

        activities = (
            self.get_object()
            .activities.filter(is_active=True, is_available=True)
            .annotate(average_rating_value=Avg("reviews__rating"))
            .order_by("-average_rating_value", "name")[:10]
        )
        serializer = ActivitySerializer(activities, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def weather_info(self, request, pk=None):
        """Return catalogue weather guidance (no external weather provider required)."""
        destination = self.get_object()
        return Response(
            {
                "destination": destination.name,
                "climate": destination.climate,
                "best_time_to_visit": destination.best_time_to_visit,
                "message": "Live weather data is not configured.",
            }
        )


@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
def trip_search(request):
    """Search destinations using either query parameters or a JSON request body."""
    criteria = request.query_params if request.method == "GET" else request.data
    query = criteria.get("q", "").strip()
    queryset = Destination.objects.filter(is_active=True).annotate(
        activity_count=Count("activities", filter=Q(activities__is_active=True), distinct=True)
    )
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(country__icontains=query)
            | Q(description__icontains=query)
        )
    if criteria.get("category"):
        queryset = queryset.filter(category=criteria["category"])
    if criteria.get("climate"):
        queryset = queryset.filter(climate=criteria["climate"])
    if criteria.get("max_daily_cost"):
        queryset = queryset.filter(avg_daily_cost__lte=criteria["max_daily_cost"])
    serializer = DestinationListSerializer(queryset.order_by("avg_daily_cost"), many=True)
    return Response({"count": queryset.count(), "results": serializer.data})
