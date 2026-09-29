import django_filters

from .models import Itinerary


class ItineraryFilter(django_filters.FilterSet):
    starts_after = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    ends_before = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")
    min_budget = django_filters.NumberFilter(field_name="budget", lookup_expr="gte")
    max_budget = django_filters.NumberFilter(field_name="budget", lookup_expr="lte")

    class Meta:
        model = Itinerary
        fields = ("status", "destination", "is_public")
