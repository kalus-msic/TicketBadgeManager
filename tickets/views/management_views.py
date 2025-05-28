from django.shortcuts import render
from ..models import Ticket, CheckIn
from ..services.ticket_service import TicketService
from ..decorators import staff_required


@staff_required
def ticket_management_dashboard(request):
    """Legacy management dashboard - redirects to main dashboard."""
    # This view is kept for backward compatibility
    # In the future, it should redirect to the main dashboard
    stats = TicketService.get_statistics()
    recent_checkins = CheckIn.objects.select_related('ticket').order_by('-check_in_time')[:10]
    
    context = {
        'total_tickets': stats['total'],
        'valid_tickets': stats['valid'],
        'used_tickets': stats['used'],
        'total_checkins': stats['checkins'],
        'recent_checkins': recent_checkins,
    }
    
    return render(request, 'tickets/ticket_management.html', context)