import logging
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.core.exceptions import ValidationError
from ..models import Log

logger = logging.getLogger(__name__)


def handle_view_errors(view_func):
    """Decorator to handle errors in views consistently."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ValidationError as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, str(e))
            return render(request, 'tickets/error.html', {'error': str(e)})
        except Exception as e:
            logger.error(f"View error in {view_func.__name__}: {e}", exc_info=True)
            
            # Log to database
            Log.objects.create(
                event_type='ERROR',
                message=f"View error in {view_func.__name__}: {str(e)}"
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
            
            messages.error(request, 'An unexpected error occurred. Please try again.')
            return render(request, 'tickets/error.html', {
                'error': 'An unexpected error occurred'
            })
    
    return wrapper


def handle_ajax_errors(view_func):
    """Decorator specifically for AJAX views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"AJAX error in {view_func.__name__}: {e}", exc_info=True)
            return JsonResponse({
                'success': False, 
                'error': 'An unexpected error occurred'
            }, status=500)
    
    return wrapper


class TicketError(Exception):
    """Base exception for ticket-related errors."""
    pass


class TicketNotFoundError(TicketError):
    """Raised when a ticket is not found."""
    pass


class TicketAlreadyUsedError(TicketError):
    """Raised when attempting to use an already used ticket."""
    pass


class ImportError(TicketError):
    """Raised when import fails."""
    pass