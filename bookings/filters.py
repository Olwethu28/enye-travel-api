import django_filters

from .models import Booking


class BookingFilter(django_filters.FilterSet):
    booked_after = django_filters.DateFilter(field_name="booking_date", lookup_expr="gte")
    booked_before = django_filters.DateFilter(field_name="booking_date", lookup_expr="lte")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Booking
        fields = ("status", "itinerary", "accommodation", "activity")
