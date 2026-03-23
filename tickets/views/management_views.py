from django.shortcuts import render, get_object_or_404
from ..models import Ticket, CheckIn, Event
from ..services.ticket_service import TicketService
from ..decorators import staff_required


@staff_required
def ticket_management_dashboard(request, event_pk):
    """Legacy management dashboard - redirects to main dashboard."""
    event = get_object_or_404(Event, pk=event_pk)
    # This view is kept for backward compatibility
    # In the future, it should redirect to the main dashboard
    stats = TicketService.get_statistics(event=event)
    recent_checkins = CheckIn.objects.filter(ticket__event=event).select_related('ticket').order_by('-check_in_time')[:10]

    context = {
        'event': event,
        'total_tickets': stats['total'],
        'valid_tickets': stats['valid'],
        'used_tickets': stats['used'],
        'total_checkins': stats['checkins'],
        'recent_checkins': recent_checkins,
    }

    return render(request, 'tickets/ticket_management.html', context)
