import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from ..models import Ticket, CheckIn, Log, Event, DEFAULT_REQUIRED_TICKET_FIELDS
from ..services.eventee_service import EventeeService
from ..decorators import staff_required
from ..utils.error_handlers import handle_view_errors
from ..utils.auth_utils import get_username_for_log
from django.urls import reverse


@staff_required
def settings(request, event_pk):
    """Display settings page."""
    import socket

    event = get_object_or_404(Event, pk=event_pk)
    api_token = event.eventee_api_token or ''

    # Test API connection
    eventee_service = EventeeService(event=event)
    api_connected, api_message = eventee_service.test_connection()

    # Get required fields
    if not event.required_ticket_fields:
        event.required_ticket_fields = DEFAULT_REQUIRED_TICKET_FIELDS
        event.save()

    # Get local IP and port
    try:
        # Better method to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = 'localhost'

    # Get port from HTTP_HOST or SERVER_PORT
    host_header = request.META.get('HTTP_HOST', '')
    if ':' in host_header:
        port = host_header.split(':')[1]
    else:
        port = request.get_port() or request.META.get('SERVER_PORT', '8000')

    # Field choices for required fields checkboxes
    field_choices = [
        ('name', 'Name'),
        ('company_name', 'Company'),
        ('email', 'E-mail'),
    ]

    context = {
        'event': event,
        'ticket_count': Ticket.objects.filter(event=event).count(),
        'checkin_count': CheckIn.objects.filter(ticket__event=event).count(),
        'logs_count': Log.objects.filter(event=event).count(),
        'eventee_token': api_token,
        'eventee_settings': event,
        'field_choices': field_choices,
        'local_ip': local_ip,
        'port': port,
        'api_connected': api_connected,
        'api_message': api_message,
    }

    return render(request, 'tickets/settings.html', context)


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def delete_all_data(request, event_pk):
    """Delete all tickets and check-ins."""
    from django.conf import settings

    event = get_object_or_404(Event, pk=event_pk)

    # Only require password if auth is enabled
    if not getattr(settings, 'DISABLE_AUTH', False):
        password = request.POST.get('password', '')

        # Simple password check - in production, use proper authentication
        if password != 'delete123':
            messages.error(request, 'Invalid password')
            return redirect('tickets:settings', event_pk=event_pk)

    with transaction.atomic():
        tickets_count = Ticket.objects.filter(event=event).count()
        checkins_count = CheckIn.objects.filter(ticket__event=event).count()

        Ticket.objects.filter(event=event).delete()

        Log.objects.create(
            event=event,
            event_type='SYSTEM',
            message=f'All data deleted by {get_username_for_log(request)}: '
                   f'{tickets_count} tickets, {checkins_count} check-ins'
        )

    messages.success(request, f'Deleted {tickets_count} tickets and {checkins_count} check-ins')
    return redirect('tickets:settings', event_pk=event_pk)


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def delete_checkins(request, event_pk):
    """Delete all check-ins and reset ticket statuses."""
    event = get_object_or_404(Event, pk=event_pk)
    with transaction.atomic():
        checkins_count = CheckIn.objects.filter(ticket__event=event).count()
        CheckIn.objects.filter(ticket__event=event).delete()

        # Reset all USED tickets to VALID
        reset_count = Ticket.objects.filter(event=event, status='USED').update(status='VALID')

        Log.objects.create(
            event=event,
            event_type='SYSTEM',
            message=f'Check-ins deleted by {get_username_for_log(request)}: '
                   f'{checkins_count} check-ins, {reset_count} tickets reset'
        )

    messages.success(request, f'Deleted {checkins_count} check-ins and reset {reset_count} tickets')
    return redirect('tickets:settings', event_pk=event_pk)


@staff_required
@require_http_methods(['POST'])
def update_eventee_token(request, event_pk):
    """Update Eventee API token."""
    event = get_object_or_404(Event, pk=event_pk)
    api_token = request.POST.get('api_token', '').strip()

    event.eventee_api_token = api_token
    event.save()

    # Test the new token
    eventee_service = EventeeService(event=event)
    connected, message = eventee_service.test_connection()

    if connected:
        messages.success(request, 'API token updated and verified successfully')
    else:
        # Always show as warning since we can't properly verify
        messages.warning(request, f'{message}')

    Log.objects.create(
        event=event,
        event_type='SYSTEM',
        message=f'Eventee API token updated by {get_username_for_log(request)}'
    )

    return redirect('tickets:settings', event_pk=event_pk)


@staff_required
@require_http_methods(['POST'])
def update_required_fields(request, event_pk):
    """Update required ticket fields configuration."""
    event = get_object_or_404(Event, pk=event_pk)
    try:
        required_fields = request.POST.getlist('required_fields')

        # Validate fields
        valid_fields = ['name', 'company_name', 'email']
        required_fields = [f for f in required_fields if f in valid_fields]

        event.required_ticket_fields = required_fields
        event.save()

        Log.objects.create(
            event=event,
            event_type='SYSTEM',
            message=f'Required fields updated by {get_username_for_log(request)}: {", ".join(required_fields)}'
        )

        messages.success(request, 'Required fields updated successfully')
        return redirect('tickets:settings', event_pk=event_pk)

    except Exception as e:
        messages.error(request, f'Failed to update required fields: {str(e)}')
        return redirect('tickets:settings', event_pk=event_pk)


@staff_required
@require_http_methods(['POST'])
def update_printer_settings(request, event_pk):
    """Update printer settings."""
    event = get_object_or_404(Event, pk=event_pk)
    auto_print = request.POST.get('auto_print_on_scan', '') == 'on'
    printer_1_name = request.POST.get('printer_1_name', 'TDP-2251').strip() or 'TDP-2251'
    printer_2_name = request.POST.get('printer_2_name', 'TDP-2252').strip() or 'TDP-2252'

    print_backend = request.POST.get('print_backend', 'direct')
    valid_backends = [c[0] for c in Event.PRINT_BACKEND_CHOICES]
    if print_backend not in valid_backends:
        print_backend = 'direct'

    event.auto_print_on_scan = auto_print
    event.printer_1_name = printer_1_name
    event.printer_2_name = printer_2_name
    event.print_backend = print_backend
    event.save()

    Log.objects.create(
        event=event,
        event_type='SYSTEM',
        message=f'Printer settings updated by {get_username_for_log(request)}: '
                f'Auto print = {auto_print}, Printer 1 = {printer_1_name}, Printer 2 = {printer_2_name}, '
                f'Backend = {print_backend}'
    )

    messages.success(request, 'Printer settings updated successfully')
    return redirect('tickets:settings', event_pk=event_pk)
