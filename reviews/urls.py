from django.urls import path

from .views import ReviewViewSet

app_name = "reviews"

urlpatterns = [
    path("mine/", ReviewViewSet.as_view({"get": "list"}), name="my-reviews"),
]
