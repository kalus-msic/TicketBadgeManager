from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.db import transaction
from ..models import Log, Event
from ..decorators import staff_required
from ..utils.error_handlers import handle_view_errors
from ..utils.auth_utils import get_username_for_log


@staff_required
def ticket_log_list(request, event_pk):
    """Display ticket logs."""
    event = get_object_or_404(Event, pk=event_pk)
    logs = Log.objects.filter(event=event).select_related('ticket').order_by('-timestamp')

    # Filter by event type if specified
    event_type = request.GET.get('event_type')
    if event_type:
        logs = logs.filter(event_type=event_type)

    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    context = {
        'event': event,
        'logs': logs_page,
        'event_type': event_type,
        'event_choices': Log.EVENT_CHOICES
    }

    return render(request, 'tickets/log.html', context)


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def delete_logs(request, event_pk):
    """Delete all logs."""
    event = get_object_or_404(Event, pk=event_pk)
    with transaction.atomic():
        count = Log.objects.filter(event=event).count()
        Log.objects.filter(event=event).delete()

        # Create a new log entry for this action
        Log.objects.create(
            event=event,
            event_type='SYSTEM',
            message=f'{count} logs deleted by {get_username_for_log(request)}'
        )

    messages.success(request, f'Deleted {count} log entries')
    return redirect('tickets:ticket_log_list', event_pk=event_pk)
