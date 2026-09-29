import django_filters

from .models import Destination


class DestinationFilter(django_filters.FilterSet):
    min_daily_cost = django_filters.NumberFilter(field_name="avg_daily_cost", lookup_expr="gte")
    max_daily_cost = django_filters.NumberFilter(field_name="avg_daily_cost", lookup_expr="lte")
    country = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Destination
        fields = ("country", "category", "climate", "is_active")
