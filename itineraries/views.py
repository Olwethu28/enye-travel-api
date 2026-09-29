"""Itinerary endpoints implemented with functions, generic views, and viewsets."""
from copy import copy

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking

from .filters import ItineraryFilter
from .models import Collaboration, DailyPlan, Itinerary
from .permissions import CanEditItinerary, IsTripOwnerOrCollaborator
from .serializers import (
    CollaborationSerializer,
    DailyPlanSerializer,
    ItineraryCreateUpdateSerializer,
    ItineraryDetailSerializer,
    ItineraryListSerializer,
)

def optimized_itineraries():
    """Return the common graph required by itinerary representations."""
    return (
        Itinerary.objects.select_related("owner", "destination")
        .prefetch_related(
            Prefetch(
                "collaborations",
                queryset=Collaboration.objects.select_related("user").order_by("-invited_at"),
            ),
            Prefetch(
                "daily_plans",
                queryset=DailyPlan.objects.prefetch_related("activities").order_by("day_number"),
            ),
        )
        .annotate(
            collaborators_count=Count("collaborations", distinct=True),
            bookings_count=Count("bookings", distinct=True),
        )
    )


class ItineraryViewSet(viewsets.ModelViewSet):
    """Manage accessible trips and perform collaboration-oriented trip actions."""

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ItineraryFilter
    search_fields = ["title", "description", "destination__name", "destination__country"]
    ordering_fields = ["start_date", "budget", "created_at", "title"]
    ordering = ["-start_date"]
    permission_classes = [permissions.IsAuthenticated, CanEditItinerary]

    def get_queryset(self):
        user = self.request.user
        return optimized_itineraries().filter(
            Q(owner=user) | Q(collaborators=user) | Q(is_public=True)
        ).distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return ItineraryListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return ItineraryCreateUpdateSerializer
        return ItineraryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def duplicate(self, request, pk=None):
        """Clone a trip and its daily plans for the requesting traveller."""
        source = self.get_object()
        clone = copy(source)
        clone.pk = None
        clone.id = None
        clone.owner = request.user
        clone.title = request.data.get("title", f"Copy of {source.title}")
        clone.status = Itinerary.Status.PLANNING
        clone.actual_spent = 0
        clone.itinerary_pdf = None
        clone.save()
        from budgets.models import Budget

        Budget.objects.create(itinerary=clone)
        for source_plan in source.daily_plans.all():
            activities = list(source_plan.activities.all())
            source_plan.pk = None
            source_plan.id = None
            source_plan.itinerary = clone
            source_plan.save()
            source_plan.activities.set(activities)
        clone = optimized_itineraries().get(pk=clone.pk)
        return Response(
            ItineraryDetailSerializer(clone, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def export_pdf(self, request, pk=None):
        """Export a compact printable itinerary document."""
        itinerary = self.get_object()
        lines = [
            itinerary.title,
            f"Destination: {itinerary.destination}",
            f"Dates: {itinerary.start_date} to {itinerary.end_date}",
            "",
        ]
        lines.extend(
            f"Day {plan.day_number} - {plan.title}: {plan.notes}"
            for plan in itinerary.daily_plans.all()
        )
        content = ("\n".join(lines) + "\n").encode()
        filename = f"itinerary-{itinerary.pk}.pdf"
        if request.method == "POST":
            itinerary.itinerary_pdf.save(filename, ContentFile(content), save=True)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"])
    def share_with_user(self, request, pk=None):
        """Invite or update a collaborator using user id or email."""
        itinerary = self.get_object()
        if itinerary.owner_id != request.user.id and not itinerary.collaborations.filter(
            user=request.user, role=Collaboration.Role.ADMIN
        ).exists():
            return Response({"detail": "Only owners and admins may share this trip."}, status=403)
        serializer = CollaborationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collaboration, created = Collaboration.objects.update_or_create(
            itinerary=itinerary,
            user=serializer.validated_data["user"],
            defaults={"role": serializer.validated_data.get("role", Collaboration.Role.VIEWER)},
        )
        return Response(
            CollaborationSerializer(collaboration).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def upcoming_trips(self, request):
        """List non-cancelled trips which have not yet ended."""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            end_date__gte=timezone.localdate()
        ).exclude(status=Itinerary.Status.CANCELLED)
        page = self.paginate_queryset(queryset)
        serializer = ItineraryListSerializer(
            page or queryset, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ItineraryListCreateView(generics.ListCreateAPIView):
    """Generic-view alternative for listing and creating the user's trips."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ItineraryFilter
    search_fields = ["title", "destination__name"]
    ordering_fields = ["start_date", "budget"]

    def get_queryset(self):
        return optimized_itineraries().filter(
            Q(owner=self.request.user) | Q(collaborators=self.request.user)
        ).distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ItineraryCreateUpdateSerializer
        return ItineraryListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TripCollaborationView(APIView):
    """List, create, change, or remove collaborators on one itinerary."""

    permission_classes = [permissions.IsAuthenticated]

    def get_itinerary(self, request, pk, write=False):
        itinerary = get_object_or_404(optimized_itineraries(), pk=pk)
        permission = CanEditItinerary() if write else IsTripOwnerOrCollaborator()
        if not permission.has_object_permission(request, self, itinerary):
            self.permission_denied(request, message=permission.message)
        return itinerary

    def get(self, request, pk):
        itinerary = self.get_itinerary(request, pk)
        return Response(CollaborationSerializer(itinerary.collaborations.all(), many=True).data)

    def post(self, request, pk):
        itinerary = self.get_itinerary(request, pk, write=True)
        serializer = CollaborationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["user"].pk == itinerary.owner_id:
            return Response({"user": ["The owner is already part of the trip."]}, status=400)
        collaboration = serializer.save(itinerary=itinerary)
        return Response(CollaborationSerializer(collaboration).data, status=201)

    def patch(self, request, pk):
        itinerary = self.get_itinerary(request, pk, write=True)
        collaboration = get_object_or_404(
            itinerary.collaborations, pk=request.data.get("collaboration_id")
        )
        serializer = CollaborationSerializer(collaboration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        itinerary = self.get_itinerary(request, pk, write=True)
        collaboration = get_object_or_404(
            itinerary.collaborations, pk=request.data.get("collaboration_id")
        )
        collaboration.delete()
        return Response(status=204)


class DailyPlanListCreateView(generics.ListCreateAPIView):
    """List or add daily plans under a nested itinerary route."""

    serializer_class = DailyPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_itinerary(self):
        itinerary = get_object_or_404(optimized_itineraries(), pk=self.kwargs["itinerary_pk"])
        permission = CanEditItinerary()
        if not permission.has_object_permission(self.request, self, itinerary):
            self.permission_denied(self.request, message=permission.message)
        return itinerary

    def get_queryset(self):
        return self.get_itinerary().daily_plans.prefetch_related("activities")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["itinerary"] = self.get_itinerary()
        return context

    def perform_create(self, serializer):
        serializer.save(itinerary=self.get_itinerary())


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_trip_report(request):
    """Aggregate trip, booking, and expense totals for the authenticated user."""
    trips = Itinerary.objects.filter(
        Q(owner=request.user) | Q(collaborators=request.user)
    ).distinct()
    trip_totals = trips.aggregate(
        total_budget=Sum("budget"),
        total_spent=Sum("actual_spent"),
        total_trips=Count("id", distinct=True),
    )
    booking_totals = Booking.objects.filter(user=request.user).aggregate(
        booking_value=Sum("price"), confirmed=Count("id", filter=Q(status="confirmed"))
    )
    recent = optimized_itineraries().filter(pk__in=trips.values("pk")).only(
        "id",
        "title",
        "destination__name",
        "owner__username",
        "start_date",
        "end_date",
        "budget",
        "actual_spent",
        "status",
        "is_public",
    )[:5]
    return Response(
        {
            **trip_totals,
            **booking_totals,
            "recent_trips": ItineraryListSerializer(recent, many=True).data,
        }
    )


class TripAnalyticsViewSet(viewsets.ViewSet):
    """Provide aggregate planning insights for the authenticated traveller."""

    permission_classes = [permissions.IsAuthenticated]

    def base_queryset(self):
        return Itinerary.objects.filter(
            Q(owner=self.request.user) | Q(collaborators=self.request.user)
        ).distinct()

    def list(self, request):
        data = self.base_queryset().aggregate(
            total_trips=Count("id"),
            total_budget=Sum("budget"),
            total_spent=Sum("actual_spent"),
        )
        return Response(data)

    @action(detail=False, methods=["get"])
    def budget_summary(self, request):
        rows = self.base_queryset().values("status").annotate(
            trips=Count("id"), budget=Sum("budget"), spent=Sum("actual_spent")
        ).order_by("status")
        return Response(list(rows))

    @action(detail=False, methods=["get"])
    def destination_preferences(self, request):
        rows = self.base_queryset().values(
            "destination__country", "destination__category"
        ).annotate(trips=Count("id")).order_by("-trips")
        return Response(list(rows))
