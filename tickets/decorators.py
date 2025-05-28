from functools import wraps
from django.contrib.auth.decorators import login_required as django_login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django.conf import settings


def login_required_ajax(view_func):
    """Login required decorator that returns JSON for AJAX requests."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip authentication if disabled in settings
        if getattr(settings, 'DISABLE_AUTH', False):
            # Create anonymous user-like object for logging
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                from django.contrib.auth.models import AnonymousUser
                request.user = AnonymousUser()
            return view_func(request, *args, **kwargs)
            
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            else:
                messages.warning(request, 'Please log in to access this page.')
                return redirect('admin:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Decorator to require staff status."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip authentication if disabled in settings
        if getattr(settings, 'DISABLE_AUTH', False):
            # Create anonymous user-like object for logging
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                from django.contrib.auth.models import AnonymousUser
                request.user = AnonymousUser()
            return view_func(request, *args, **kwargs)
            
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            else:
                return redirect('admin:login')
        
        if not request.user.is_staff:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Staff access required'
                }, status=403)
            else:
                messages.error(request, 'You need staff access to view this page.')
                return redirect('tickets:index')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# Export rate limiting decorators with sensible defaults
ticket_verify_ratelimit = ratelimit(key='ip', rate='60/m', method='POST')
import_ratelimit = ratelimit(key='ip', rate='10/h', method='POST')
api_ratelimit = ratelimit(key='ip', rate='100/h')