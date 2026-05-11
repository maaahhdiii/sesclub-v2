from django.contrib import admin

from .models import Request


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'request_type', 'status', 'created_at')
    list_filter = ('status', 'request_type', 'created_at')
    search_fields = ('title', 'description', 'user__email', 'user__username')
    readonly_fields = ('request_id', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        # Ensure all requests are visible in the Django Admin panel
        return super().get_queryset(request)
