import socket
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Log
from ..services.ticket_service import TicketService
from ..services.printing_service import PrintingService
from ..decorators import login_required_ajax, ticket_verify_ratelimit
from ..utils.error_handlers import handle_ajax_errors
from ..utils.validators import sanitize_string


@login_required_ajax
def scanner_page(request, printer_queue='1'):
    """Display QR code scanner page."""
    host = request.get_host()
    
    # Check if accessed via HTTPS
    is_https = request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https'
    
    # Get printer queue from URL parameter or use default
    printer_queue = request.GET.get('printer_queue', printer_queue)
    
    return render(request, 'tickets/scanner.html', {
        'host': host,
        'is_https': is_https,
        'mode': request.GET.get('mode', 'verify'),
        'printer_queue': printer_queue
    })


@login_required_ajax
def scanner_page1(request):
    """Scanner page with printer queue 1."""
    return scanner_page(request, printer_queue='1')


@login_required_ajax
def scanner_page2(request):
    """Scanner page with printer queue 2."""
    return scanner_page(request, printer_queue='2')


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
            
            # Override printer based on printer_queue
            if printer_queue == '2':
                printing_service.printer_name = 'TDP-2252'
            else:
                printing_service.printer_name = 'TDP-2251'
            
            print_success = printing_service.print_ticket({
                'qr_code': ticket.qr_code,
                'name': ticket.name,
                'company_name': ticket.company_name,
                'event_name': ticket.event_name
            })
            
            if print_success:
                # Log successful print
                Log.objects.create(
                    ticket=ticket,
                    ticket_qr=ticket.qr_code,
                    event_type='PRINT',
                    message=f"Label printed successfully on Scanner {printer_queue} (Printer: {printing_service.printer_name})"
                )
                response_data['print_success'] = True
            else:
                import platform
                if platform.system() != "Windows":
                    os_name = platform.system()
                    error_msg = (
                        f'Label printing failed on {os_name}. '
                        f'TSC thermal printers require Windows with TSCLIB.dll library.'
                    )
                    response_data['print_warning'] = error_msg + ' The ticket was checked in successfully.'
                    
                    # Log the print failure
                    Log.objects.create(
                        ticket=ticket,
                        ticket_qr=ticket.qr_code,
                        event_type='ERROR',
                        message=f"Print failed from Scanner {printer_queue}: {error_msg}"
                    )
                else:
                    error_msg = 'Label printing failed - please check printer connection and configuration.'
                    response_data['print_warning'] = error_msg + ' The ticket was checked in successfully.'
                    
                    # Log the print failure
                    Log.objects.create(
                        ticket=ticket,
                        ticket_qr=ticket.qr_code,
                        event_type='ERROR',
                        message=f"Print failed from Scanner {printer_queue}: {error_msg}"
                    )
    
    return JsonResponse(response_data)


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