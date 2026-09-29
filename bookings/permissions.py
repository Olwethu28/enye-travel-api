from rest_framework.permissions import BasePermission


class IsBookingOwner(BasePermission):
    """Restrict booking operations to the traveller who placed it."""

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
