from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubViewSet, ClubMembershipViewSet, ClubReviewViewSet

router = DefaultRouter()
router.register(r'clubs', ClubViewSet, basename='club')
router.register(r'memberships', ClubMembershipViewSet, basename='membership')
club_review_list = ClubReviewViewSet.as_view({'get': 'list', 'post': 'create'})
club_review_detail = ClubReviewViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'})

urlpatterns = [
    path('', include(router.urls)),
    path('clubs/<uuid:club_pk>/reviews/', club_review_list, name='club-reviews'),
    path('clubs/<uuid:club_pk>/reviews/<int:pk>/', club_review_detail, name='club-review-detail'),
]
