from django.urls import path, include
from .views import (
    RegisterView,
    ProfileView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    GoogleStudentLoginView,
    GoogleClubLoginView,
    GoogleCompleteView,
    GoogleSuccessView,
    GoogleErrorView,
    VerifyCodeView,
    ResendCodeView,
)

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/me/', ProfileView.as_view(), name='profile'),
    path('auth/google/login/student/', GoogleStudentLoginView.as_view(), name='google_login_student'),
    path('auth/google/login/club/', GoogleClubLoginView.as_view(), name='google_login_club'),
    path('auth/google/complete/<str:backend>/', GoogleCompleteView.as_view(), name='google_complete'),
    path('auth/google/', include('social_django.urls', namespace='social')),
    path('auth/google/success/', GoogleSuccessView.as_view(), name='google_success'),
    path('auth/google/error/', GoogleErrorView.as_view(), name='google_error'),
    path('auth/verify-code/', VerifyCodeView.as_view(), name='verify_code'),
    path('auth/resend-code/', ResendCodeView.as_view(), name='resend_code'),
]
