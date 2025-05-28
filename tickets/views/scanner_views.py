import socket
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..services.ticket_service import TicketService
from ..services.printing_service import PrintingService
from ..decorators import login_required_ajax, ticket_verify_ratelimit
from ..utils.error_handlers import handle_ajax_errors
from ..utils.validators import sanitize_string


@login_required_ajax
def scanner_page(request):
    """Display QR code scanner page."""
    host = request.get_host()
    
    # Check if accessed via HTTPS
    is_https = request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https'
    
    return render(request, 'tickets/scanner.html', {
        'host': host,
        'is_https': is_https,
        'mode': request.GET.get('mode', 'verify')
    })


def scanner_page1(request):
    """Scanner page with mode 1."""
    return scanner_page(request)


def scanner_page2(request):
    """Scanner page with mode 2."""
    return scanner_page(request)


@require_http_methods(['POST'])
@ticket_verify_ratelimit
@handle_ajax_errors
def verify_ticket(request):
    """Verify ticket and optionally print badge."""
    qr_code = sanitize_string(request.POST.get('qr_code', ''))
    print_badge = request.POST.get('print', 'false').lower() == 'true'
    
    if not qr_code:
        return JsonResponse({
            'success': False,
            'message': 'QR code is required'
        })
    
    # Verify ticket using service
    success, message, ticket = TicketService.verify_ticket(qr_code)
    
    response_data = {
        'success': success,
        'message': message
    }
    
    if ticket:
        response_data['ticket'] = {
            'id': ticket.id,
            'qr_code': ticket.qr_code,
            'name': ticket.name,
            'company': ticket.company_name or '',
            'status': ticket.get_status_display()
        }
        
        # Print badge if requested and verification successful
        if success and print_badge:
            printing_service = PrintingService()
            print_success = printing_service.print_ticket({
                'qr_code': ticket.qr_code,
                'name': ticket.name,
                'company_name': ticket.company_name,
                'event_name': ticket.event_name
            })
            
            if not print_success:
                import platform
                if platform.system() != "Windows":
                    os_name = platform.system()
                    response_data['print_warning'] = (
                        f'Label printing is not available on {os_name}. '
                        f'TSC thermal printers require Windows with TSCLIB.dll library. '
                        f'The ticket was checked in successfully.'
                    )
                else:
                    response_data['print_warning'] = (
                        'Label printing failed - please check printer connection and configuration. '
                        'The ticket was checked in successfully.'
                    )
    
    return JsonResponse(response_data)


@login_required_ajax
def check_server_status(request):
    """Check if server is running and get local IP."""
    try:
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Get port from request
        port = request.META.get('SERVER_PORT', '8000')
        
        # Check if port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', int(port)))
        sock.close()
        port_open = result == 0
        
        # Check if accessible from network
        accessible = False
        if port_open:
            try:
                # Try to connect using the local IP
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((local_ip, int(port)))
                sock.close()
                accessible = result == 0
            except:
                accessible = False
        
        return JsonResponse({
            'port_open': port_open,
            'accessible': accessible,
            'port': port,
            'local_ip': local_ip
        })
    except Exception as e:
        return JsonResponse({
            'port_open': False,
            'accessible': False,
            'error': str(e)
        })