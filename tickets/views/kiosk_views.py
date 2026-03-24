"""Kiosk mode for self-service check-in."""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.translation import gettext as _
from ..models import Ticket, CheckIn, Log, Event
from ..services.ticket_service import TicketService
from ..utils.validators import sanitize_string
from ..utils.error_handlers import handle_ajax_errors
from ..utils.auth_utils import get_username_for_log


def kiosk_mode(request, event_pk):
    """Display kiosk mode for self-service check-in."""
    event = get_object_or_404(Event, pk=event_pk)
    # Kiosk mode doesn't require authentication
    return render(request, 'tickets/kiosk.html', {'event': event})


@require_http_methods(['POST'])
@handle_ajax_errors
@xframe_options_exempt  # Allow fullscreen
def kiosk_verify(request, event_pk):
    """Verify ticket in kiosk mode and print badge if successful."""
    event = get_object_or_404(Event, pk=event_pk)
    qr_code = sanitize_string(request.POST.get('qr_code', ''))
    printer_queue = request.POST.get('printer_queue', '1')  # Default to printer 1

    if not qr_code:
        return JsonResponse({
            'success': False,
            'message': _('Please scan your ticket QR code')
        })

    # Log all scan attempts for security
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')

    # Verify ticket using service
    success, message, ticket = TicketService.verify_ticket(qr_code, event=event)

    response_data = {
        'success': success,
        'message': message
    }

    # Always log scan attempts
    if ticket:
        if success:
            # Print badge for successful verification
            print_success = False
            print_dispatched = False
            from tickets.printing import PrintManager
            pm = PrintManager(event)
            result = pm.print_ticket({
                'qr_code': ticket.qr_code,
                'name': ticket.name,
                'company_name': ticket.company_name,
                'event_name': ticket.event.name if ticket.event else ''
            }, printer_queue)

            if result['status'] == 'printed':
                response_data['badge_printed'] = True
                response_data['print_message'] = _('Your badge is printing...')
                print_success = True
            elif result['status'] == 'print_required':
                response_data['print_backend'] = result['backend']
                response_data['print_data'] = result['data']
                response_data['print_printer'] = result['printer']
                print_dispatched = True  # Will be handled client-side
            else:
                response_data['print_warning'] = result.get(
                    'message', _('Badge printing failed.')
                )

            if print_success:
                print_status_msg = 'badge printed'
            elif print_dispatched:
                print_status_msg = 'badge sent to client'
            else:
                print_status_msg = 'print failed'

            Log.objects.create(
                ticket=ticket,
                event=event,
                event_type='CHECKIN',
                message=f'Kiosk check-in from IP {client_ip}, {print_status_msg}'
            )
        else:
            Log.objects.create(
                ticket=ticket,
                event=event,
                event_type='ERROR',
                message=f'Kiosk scan failed from IP {client_ip}: {message}'
            )
    else:
        # Log invalid QR codes for security monitoring
        Log.objects.create(
            ticket_qr=qr_code[:100],  # Limit length for security
            event=event,
            event_type='ERROR',
            message=f'Kiosk scan - invalid QR code from IP {client_ip}'
        )

    if ticket and success:
        response_data['ticket'] = {
            'name': ticket.name,
            'company': ticket.company_name or '',
        }
        # Add welcome message
        response_data['welcome_message'] = _('Welcome %(name)s!') % {'name': ticket.name}

    return JsonResponse(response_data)
