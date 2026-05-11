from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from . import static_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-page/', static_views.admin_page, name='admin-page'),
    path('president-page/', static_views.president_page, name='president-page'),
    path('', RedirectView.as_view(url='/api/v1/health/'), name='root-redirect'),
    path('student/', static_views.student, name='student-page'),
    path('club/', static_views.club, name='club-page'),
    path('api/v1/', include('users.api_urls')),
    path('api/v1/', include('clubs.urls')),
    path('api/v1/', include('events.urls')),
    path('api/v1/', include('app_requests.urls')),
    path('api/v1/', include('communications.urls')),
    path('api/v1/', include('audit.urls')),
    path('api/v1/', include('users.urls')),
    path('api/v1/health/', include('health.urls')),
]
