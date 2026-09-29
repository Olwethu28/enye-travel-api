"""Authentication and profile endpoints."""
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .serializers import RegisterSerializer, UserProfileSerializer


class RegisterView(generics.CreateAPIView):
    """Create a traveller account and return an initial JWT token pair."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the authenticated traveller profile."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def travel_preferences(request):
    """Read or partially update the authenticated user's travel preferences."""
    if request.method == "PATCH":
        serializer = UserProfileSerializer(
            request.user,
            data={"travel_preferences": request.data.get("travel_preferences", request.data)},
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(UserProfileSerializer(request.user, context={"request": request}).data)
