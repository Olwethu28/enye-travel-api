"""Review creation and community feedback endpoints."""
from django.db.models import F
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Review
from .serializers import ReviewCreateUpdateSerializer, ReviewListSerializer, ReviewSerializer


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or obj.user_id == request.user.id


class ReviewViewSet(viewsets.ModelViewSet):
    """Create reviews, browse feedback, and mark reviews as helpful."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsReviewOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "user__username"]
    ordering_fields = ["rating", "helpful_count", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ReviewListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return ReviewCreateUpdateSerializer
        return ReviewSerializer

    def get_queryset(self):
        queryset = Review.objects.select_related(
            "user", "destination", "accommodation", "activity"
        )
        for field in ("destination", "accommodation", "activity", "rating"):
            if self.request.query_params.get(field):
                queryset = queryset.filter(**{field: self.request.query_params[field]})
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def helpful(self, request, pk=None):
        Review.objects.filter(pk=self.get_object().pk).update(helpful_count=F("helpful_count") + 1)
        review = self.get_queryset().get(pk=pk)
        return Response(self.get_serializer(review).data)
