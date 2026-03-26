import json
import socket
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Log, Event, Ticket
from ..services.ticket_service import TicketService
from ..decorators import login_required_ajax, staff_required, ticket_verify_ratelimit
from ..utils.error_handlers import handle_ajax_errors
from ..utils.validators import sanitize_string


@login_required_ajax
def scanner_page(request, event_pk, printer_queue='1'):
    """Display QR code scanner page."""
    event = get_object_or_404(Event, pk=event_pk)

    host = request.get_host()

    # Check if accessed via HTTPS
    is_https = request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https'

    # Get printer queue from URL parameter or use default
    printer_queue = request.GET.get('printer_queue', printer_queue)

    # Get auto print setting from event
    auto_print = event.auto_print_on_scan

    return render(request, 'tickets/scanner.html', {
        'event': event,
        'host': host,
        'is_https': is_https,
        'mode': request.GET.get('mode', 'verify'),
        'printer_queue': printer_queue,
        'auto_print_on_scan': auto_print
    })


@login_required_ajax
def scanner_page1(request, event_pk):
    """Scanner page with printer queue 1."""
    return scanner_page(request, event_pk, printer_queue='1')


@login_required_ajax
def scanner_page2(request, event_pk):
    """Scanner page with printer queue 2."""
    return scanner_page(request, event_pk, printer_queue='2')


@require_http_methods(['POST'])
@ticket_verify_ratelimit
@handle_ajax_errors
def verify_ticket(request, event_pk):
    """Verify ticket and optionally print badge."""
    event = get_object_or_404(Event, pk=event_pk)
    qr_code = sanitize_string(request.POST.get('qr_code', ''))
    print_badge = request.POST.get('print', 'false').lower() == 'true'
    verify_badge = request.POST.get('verify', 'true').lower() == 'true'
    printer_queue = request.POST.get('printer_queue', '1')

    if not qr_code:
        return JsonResponse({
            'success': False,
            'message': 'QR code is required'
        })

    # Get ticket first
    ticket = TicketService.get_ticket_by_qr(qr_code)
    if not ticket:
        Log.objects.create(
            ticket_qr=qr_code,
            event_type='ERROR',
            event=event,
            message=f'Ticket not found: {qr_code}'
        )
        return JsonResponse({
            'success': False,
            'message': 'Ticket not found'
        })

    success = True
    message = ""

    # Perform verification if requested
    if verify_badge:
        success, message, _ = TicketService.verify_ticket(qr_code, event=event)
    else:
        message = "Status check"
        # If not verifying, we just return current status info
        if ticket.status == 'USED':
            message = "Ticket already used"
        elif ticket.status == 'CANCELLED':
            message = "Ticket cancelled"
        else:
            message = "Ticket is valid"

    response_data = {
        'success': success,
        'message': message,
        'ticket': {
            'id': ticket.id,
            'qr_code': ticket.qr_code,
            'name': ticket.name,
            'company': ticket.company_name or '',
            'status': ticket.get_status_display()
        }
    }

    # Print badge if requested
    # If verify_badge is False, we print regardless of status (unless it's CANCELLED maybe?)
    # If verify_badge is True, we only print if verification was successful
    should_print = False
    if print_badge:
        if verify_badge:
            should_print = success
        else:
            # Print only mode - print regardless of USED status, but maybe not if CANCELLED
            should_print = ticket.status != 'CANCELLED'
            if ticket.status == 'CANCELLED':
                response_data['print_warning'] = "Cannot print label for cancelled ticket"

    if should_print:
        from tickets.printing import PrintManager
        pm = PrintManager(event)
        result = pm.print_ticket({
            'qr_code': ticket.qr_code,
            'name': ticket.name,
            'company_name': ticket.company_name,
            'event_name': ticket.event.name if ticket.event else '',
            'ticket_id': ticket.id,
        }, printer_queue)

        if result['status'] == 'printed':
            Log.objects.create(
                ticket=ticket, ticket_qr=ticket.qr_code, event=event,
                event_type='PRINT',
                message=f"Label printed on Scanner {printer_queue} "
                        f"(Printer: {pm.get_printer_name(printer_queue)})"
            )
            response_data['print_success'] = True
        elif result['status'] == 'print_required':
            # Client-side printing — send data to JS
            response_data['print_backend'] = result['backend']
            response_data['print_data'] = result['data']
            response_data['print_printer'] = result['printer']
            Log.objects.create(
                ticket=ticket, ticket_qr=ticket.qr_code, event=event,
                event_type='PRINT',
                message=f"Badge sent to {result['backend']} client (Scanner {printer_queue}, Printer: {result['printer']})"
            )
        elif result['status'] == 'queued':
            Log.objects.create(
                event=ticket.event,
                ticket=ticket,
                ticket_qr=ticket.qr_code,
                event_type='PRINT',
                message=f"Badge queued for agent — queue {printer_queue}",
            )
            response_data['print_queued'] = True
        else:
            response_data['print_warning'] = result.get(
                'message', 'Label printing failed'
            )
            Log.objects.create(
                ticket=ticket, ticket_qr=ticket.qr_code, event=event,
                event_type='ERROR',
                message=f"Print failed from Scanner {printer_queue}: "
                        f"{result.get('message', 'unknown error')}"
            )

    return JsonResponse(response_data)


@require_http_methods(['POST'])
@ticket_verify_ratelimit
@staff_required
@handle_ajax_errors
def print_confirm(request, event_pk):
    """Confirm print result from client-side backend (WebUSB/Agent)."""
    event = get_object_or_404(Event, pk=event_pk)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

    ticket_id = data.get('ticket_id')
    success = data.get('success', False)
    printer_queue = sanitize_string(str(data.get('printer_queue', '1')))[:10]
    error_msg = sanitize_string(str(data.get('error', '')))[:500]

    ticket = None
    if ticket_id:
        ticket = Ticket.objects.filter(pk=ticket_id, event=event).first()

    if success:
        Log.objects.create(
            ticket=ticket,
            ticket_qr=ticket.qr_code if ticket else '',
            event=event,
            event_type='PRINT',
            message=f"Label printed via {event.print_backend} on queue {printer_queue}"
        )
    else:
        Log.objects.create(
            ticket=ticket,
            ticket_qr=ticket.qr_code if ticket else '',
            event=event,
            event_type='ERROR',
            message=f"Print failed via {event.print_backend}: {error_msg}"
        )

    return JsonResponse({'success': True})


@login_required_ajax
def check_server_status(request):
    """Check if server is running and get local IP."""
    import platform

    try:
        # Get local IP - better method that works on all platforms
        local_ip = None
        try:
            # Try to connect to Google DNS to find our local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            # Fallback to hostname method
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

        # Get actual port from the request
        # When using runsslserver, the port is in HTTP_HOST
        host_header = request.META.get('HTTP_HOST', '')
        if ':' in host_header:
            port = host_header.split(':')[1]
        else:
            # Fallback to SERVER_PORT or default
            port = request.META.get('SERVER_PORT', '8000')

        # Additional check - get the actual port we're listening on
        actual_port = request.get_port()
        if actual_port:
            port = str(actual_port)

        # Check if server is accessible locally
        port_open = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', int(port)))
            sock.close()
            port_open = result == 0
        except:
            pass

        # Check if accessible from network (using actual local IP)
        accessible = False
        if port_open and local_ip:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((local_ip, int(port)))
                sock.close()
                accessible = result == 0
            except:
                accessible = False

        # Get all network interfaces for more info
        all_ips = []
        if platform.system() == "Windows":
            # Windows specific
            hostname = socket.gethostname()
            all_ips = socket.gethostbyname_ex(hostname)[2]
        else:
            # Linux/Mac - try to get all IPs
            try:
                import netifaces
                for interface in netifaces.interfaces():
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            ip = addr['addr']
                            if ip != '127.0.0.1':
                                all_ips.append(ip)
            except:
                all_ips = [local_ip] if local_ip else []

        return JsonResponse({
            'port_open': port_open,
            'accessible': accessible,
            'port': port,
            'local_ip': local_ip,
            'all_ips': all_ips,
            'platform': platform.system()
        })
    except Exception as e:
        return JsonResponse({
            'port_open': False,
            'accessible': False,
            'error': str(e),
            'local_ip': 'unknown',
            'port': 'unknown'
        })
