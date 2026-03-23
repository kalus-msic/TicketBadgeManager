"""Search functionality views."""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ..models import Ticket, Event
from ..decorators import login_required_ajax
from ..utils.validators import sanitize_string
from ..utils.text_utils import normalize_text


@login_required_ajax
def search_tickets_by_name(request, event_pk):
    """Search tickets by name for quick check-in."""
    event = get_object_or_404(Event, pk=event_pk)
    query = sanitize_string(request.GET.get('q', ''))

    if len(query) < 2:
        return JsonResponse({'results': []})

    # Get all valid tickets for this event
    all_tickets = Ticket.objects.filter(event=event, status='VALID')

    # Normalize the search query
    normalized_query = normalize_text(query)

    # Filter tickets using normalized text
    matching_tickets = []
    for ticket in all_tickets:
        normalized_name = normalize_text(ticket.name or '')
        normalized_company = normalize_text(ticket.company_name or '')

        # Check if normalized query matches
        if normalized_query in normalized_name or normalized_query in normalized_company:
            matching_tickets.append({
                'id': ticket.id,
                'qr_code': ticket.qr_code,
                'name': ticket.name,
                'company_name': ticket.company_name
            })

            # Limit to 10 results
            if len(matching_tickets) >= 10:
                break

    return JsonResponse({'results': matching_tickets})
