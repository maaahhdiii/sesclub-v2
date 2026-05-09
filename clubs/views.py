from rest_framework import viewsets, permissions
from .models import Club, ClubMembership
from .serializers import ClubSerializer, ClubMembershipSerializer

class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    permission_classes = [permissions.IsAuthenticated]

class ClubMembershipViewSet(viewsets.ModelViewSet):
    queryset = ClubMembership.objects.all()
    serializer_class = ClubMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
