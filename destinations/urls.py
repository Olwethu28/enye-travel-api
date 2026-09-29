from django.urls import path

from .views import trip_search

app_name = "destinations"

urlpatterns = [path("search/", trip_search, name="trip-search")]
