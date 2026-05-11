from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Custom DRF exception handler that returns clearer 401 messages."""
    response = exception_handler(exc, context)
    if response is None:
        return response

    # Improve 401 Unauthorized message
    if getattr(response, 'status_code', None) == 401:
        response.data = {
            'detail': 'Authentication credentials were not provided or are invalid. Obtain a valid JWT and include it as "Authorization: Bearer <token>".',
            'code': 'unauthorized',
        }

    return response
