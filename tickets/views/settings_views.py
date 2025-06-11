import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from ..models import Ticket, CheckIn, Log, AppSettings, DEFAULT_REQUIRED_TICKET_FIELDS
from ..services.eventee_service import EventeeService
from ..decorators import staff_required
from ..utils.error_handlers import handle_view_errors
from ..utils.auth_utils import get_username_for_log
from django.urls import reverse


@staff_required
def settings(request):
    """Display settings page."""
    import socket
    
    app_settings = AppSettings.objects.first()
    api_token = app_settings.eventee_api_token if app_settings else ''
    
    # Test API connection
    eventee_service = EventeeService()
    api_connected, api_message = eventee_service.test_connection()
    
    # Get required fields
    if not app_settings:
        # Create default settings if they don't exist
        app_settings = AppSettings.objects.create(
            required_ticket_fields=DEFAULT_REQUIRED_TICKET_FIELDS
        )
    elif not app_settings.required_ticket_fields:
        # Set default required fields if empty
        app_settings.required_ticket_fields = DEFAULT_REQUIRED_TICKET_FIELDS
        app_settings.save()
    
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
        'ticket_count': Ticket.objects.count(),
        'checkin_count': CheckIn.objects.count(),
        'logs_count': Log.objects.count(),
        'eventee_token': api_token,
        'eventee_settings': app_settings,
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
def delete_all_data(request):
    """Delete all tickets and check-ins."""
    from django.conf import settings
    
    # Only require password if auth is enabled
    if not getattr(settings, 'DISABLE_AUTH', False):
        password = request.POST.get('password', '')
        
        # Simple password check - in production, use proper authentication
        if password != 'delete123':
            messages.error(request, 'Invalid password')
            return redirect('tickets:settings')
    
    with transaction.atomic():
        tickets_count = Ticket.objects.count()
        checkins_count = CheckIn.objects.count()
        
        Ticket.objects.all().delete()
        CheckIn.objects.all().delete()
        
        Log.objects.create(
            event_type='SYSTEM',
            message=f'All data deleted by {get_username_for_log(request)}: '
                   f'{tickets_count} tickets, {checkins_count} check-ins'
        )
    
    messages.success(request, f'Deleted {tickets_count} tickets and {checkins_count} check-ins')
    return redirect('tickets:settings')


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def delete_checkins(request):
    """Delete all check-ins and reset ticket statuses."""
    with transaction.atomic():
        checkins_count = CheckIn.objects.count()
        CheckIn.objects.all().delete()
        
        # Reset all USED tickets to VALID
        reset_count = Ticket.objects.filter(status='USED').update(status='VALID')
        
        Log.objects.create(
            event_type='SYSTEM',
            message=f'Check-ins deleted by {get_username_for_log(request)}: '
                   f'{checkins_count} check-ins, {reset_count} tickets reset'
        )
    
    messages.success(request, f'Deleted {checkins_count} check-ins and reset {reset_count} tickets')
    return redirect('tickets:settings')


@staff_required
@require_http_methods(['POST'])
def update_eventee_token(request):
    """Update Eventee API token."""
    api_token = request.POST.get('api_token', '').strip()
    
    eventee_service = EventeeService()
    if eventee_service.update_api_token(api_token):
        # Test the new token
        connected, message = eventee_service.test_connection()
        
        if connected:
            messages.success(request, 'API token updated and verified successfully')
        else:
            # Always show as warning since we can't properly verify
            messages.warning(request, f'{message}')
        
        Log.objects.create(
            event_type='SYSTEM',
            message=f'Eventee API token updated by {get_username_for_log(request)}'
        )
    else:
        messages.error(request, 'Failed to update API token')
    
    return redirect('tickets:settings')


@staff_required
@require_http_methods(['POST'])
def update_required_fields(request):
    """Update required ticket fields configuration."""
    try:
        required_fields = request.POST.getlist('required_fields')
        
        # Validate fields
        valid_fields = ['name', 'company_name', 'email']
        required_fields = [f for f in required_fields if f in valid_fields]
        
        # Update or create settings
        settings_obj, created = AppSettings.objects.get_or_create(
            defaults={'required_ticket_fields': required_fields}
        )
        
        if not created:
            settings_obj.required_ticket_fields = required_fields
            settings_obj.save()
        
        Log.objects.create(
            event_type='SYSTEM',
            message=f'Required fields updated by {get_username_for_log(request)}: {", ".join(required_fields)}'
        )
        
        messages.success(request, 'Required fields updated successfully')
        return redirect('tickets:settings')
        
    except Exception as e:
        messages.error(request, f'Failed to update required fields: {str(e)}')
        return redirect('tickets:settings')


@staff_required
@require_http_methods(['POST'])
def update_printer_settings(request):
    """Update printer settings."""
    auto_print = request.POST.get('auto_print_on_scan', '') == 'on'
    
    settings_obj = AppSettings.objects.first()
    if not settings_obj:
        settings_obj = AppSettings.objects.create()
    
    settings_obj.auto_print_on_scan = auto_print
    settings_obj.save()
    
    Log.objects.create(
        event_type='SYSTEM',
        message=f'Printer settings updated by {get_username_for_log(request)}: Auto print on scan = {auto_print}'
    )
    
    messages.success(request, 'Printer settings updated successfully')
    return redirect('tickets:settings')