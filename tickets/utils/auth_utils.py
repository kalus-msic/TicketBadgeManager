"""Authentication utility functions."""
from django.conf import settings


def get_username_for_log(request):
    """Get username for logging, handling anonymous users consistently."""
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user.username
    return 'Anonymous'


def is_auth_required():
    """Check if authentication is required."""
    return not getattr(settings, 'DISABLE_AUTH', False)