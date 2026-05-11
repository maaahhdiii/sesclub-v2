from django.http import JsonResponse
from django.utils import timezone


def health(request):
    """Simple health check for the API root."""
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
    })
