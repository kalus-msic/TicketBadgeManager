import time
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from ..models import Ticket, Log, Event
from ..services.printing_service import PrintingService
from ..decorators import staff_required
from ..utils.auth_utils import get_username_for_log


@staff_required
def bulk_print(request, event_pk):
    """Display bulk print page with all tickets."""
    event = get_object_or_404(Event, pk=event_pk)
    tickets = Ticket.objects.filter(event=event).order_by('name')

    # Add print status to tickets
    for ticket in tickets:
        ticket.has_been_printed = Log.objects.filter(
            ticket=ticket,
            event_type='BULK_PRINT'
        ).exists()

    context = {
        'event': event,
        'tickets': tickets,
        'total_count': tickets.count(),
    }
    return render(request, 'tickets/bulk_print.html', context)


@staff_required
@require_http_methods(["POST"])
def bulk_print_execute(request, event_pk):
    """Execute bulk printing of selected tickets."""
    import json

    event = get_object_or_404(Event, pk=event_pk)

    try:
        data = json.loads(request.body)
        ticket_ids = data.get('ticket_ids', [])
        printer = data.get('printer', 'Printer 1')

        if not ticket_ids:
            return JsonResponse({
                'success': False,
                'error': _('No tickets selected')
            })

        # Get selected tickets scoped to event
        tickets = Ticket.objects.filter(event=event, id__in=ticket_ids)

        results = {
            'success': True,
            'printed': [],
            'failed': [],
            'total': len(ticket_ids)
        }

        # Initialize printing service
        printing_service = PrintingService()

        # Determine printer queue based on selection
        printer_queue = '2' if printer == 'Printer 2' else '1'

        # Print each ticket with delay
        for ticket in tickets:
            try:
                # Print the ticket
                print_success = printing_service.print_ticket({
                    'qr_code': ticket.qr_code,
                    'name': ticket.name,
                    'company_name': ticket.company_name or '',
                    'event_name': ticket.event.name if ticket.event else ''
                }, printer_queue, event=event)

                if print_success:
                    # Log successful print
                    Log.objects.create(
                        ticket=ticket,
                        ticket_qr=ticket.qr_code,
                        event=event,
                        event_type='BULK_PRINT',
                        message=f"Bulk printed on {printer} by {get_username_for_log(request.user)}"
                    )

                    results['printed'].append({
                        'id': ticket.id,
                        'name': ticket.name
                    })
                else:
                    results['failed'].append({
                        'id': ticket.id,
                        'name': ticket.name,
                        'error': _('Failed to print')
                    })

                # Add delay between prints
                time.sleep(0.5)

            except Exception as e:
                results['failed'].append({
                    'id': ticket.id,
                    'name': ticket.name,
                    'error': str(e)
                })

        # Add summary to results
        results['summary'] = {
            'printed_count': len(results['printed']),
            'failed_count': len(results['failed'])
        }

        return JsonResponse(results)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
