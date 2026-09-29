"""Object-level permissions shared by itinerary endpoints."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsTripOwner(BasePermission):
    """Only the itinerary owner may access the object."""

    message = "Only the trip owner may perform this action."

    def has_object_permission(self, request, view, obj):
        itinerary = getattr(obj, "itinerary", obj)
        return itinerary.owner_id == request.user.id


class IsTripOwnerOrCollaborator(BasePermission):
    """Allow owners and invited collaborators to access a trip."""

    message = "You do not have access to this itinerary."

    def has_object_permission(self, request, view, obj):
        itinerary = getattr(obj, "itinerary", obj)
        return itinerary.owner_id == request.user.id or itinerary.collaborators.filter(
            id=request.user.id
        ).exists()


class CanEditItinerary(BasePermission):
    """Owners and editor/admin collaborators write; viewers receive read-only access."""

    message = "Your collaboration role does not allow editing this itinerary."

    def has_object_permission(self, request, view, obj):
        itinerary = getattr(obj, "itinerary", obj)
        if itinerary.owner_id == request.user.id:
            return True
        collaboration = itinerary.collaborations.filter(user=request.user).only("role").first()
        if not collaboration:
            return bool(request.method in SAFE_METHODS and itinerary.is_public)
        return request.method in SAFE_METHODS or collaboration.role in {"editor", "admin"}
