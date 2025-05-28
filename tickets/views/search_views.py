"""Search functionality views."""
from django.http import JsonResponse
from django.db.models import Q
from ..models import Ticket
from ..decorators import login_required_ajax
from ..utils.validators import sanitize_string


@login_required_ajax
def search_tickets_by_name(request):
    """Search tickets by name for quick check-in."""
    query = sanitize_string(request.GET.get('q', ''))
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search in name and company name
    tickets = Ticket.objects.filter(
        Q(name__icontains=query) | Q(company_name__icontains=query),
        status='VALID'  # Only show valid tickets
    ).values('id', 'qr_code', 'name', 'company_name')[:10]
    
    return JsonResponse({'results': list(tickets)})