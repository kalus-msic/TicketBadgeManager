from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Ticket, CheckIn
from ..services.ticket_service import TicketService
from ..decorators import login_required_ajax


@login_required_ajax
def index(request):
    """Main dashboard view."""
    stats = TicketService.get_statistics()
    recent_checkins = CheckIn.objects.select_related('ticket').order_by('-check_in_time')[:10]
    
    # Prepare hourly data for chart
    import json
    hourly_data = {
        'labels': [item['hour'].strftime('%H:%M') for item in stats['checkins_by_hour']],
        'data': [item['count'] for item in stats['checkins_by_hour']]
    }
    
    context = {
        'total_tickets': stats['total'],
        'valid_tickets': stats['valid'],
        'used_tickets': stats['used'],
        'total_checkins': stats['checkins'],
        'percentage_checked_in': stats['percentage_checked_in'],
        'last_hour_checkins': stats['last_hour_checkins'],
        'checkin_trend': stats['checkin_trend'],
        'recent_checkins': recent_checkins,
        'hourly_data_json': json.dumps(hourly_data),
    }
    return render(request, 'tickets/index.html', context)