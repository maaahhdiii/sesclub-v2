from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubViewSet, ClubMembershipViewSet

router = DefaultRouter()
router.register(r'clubs', ClubViewSet, basename='club')
router.register(r'memberships', ClubMembershipViewSet, basename='membership')

urlpatterns = [
    path('', include(router.urls)),
]
