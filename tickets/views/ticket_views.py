import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from ..models import Ticket, Log, CheckIn, Event
from ..forms import TicketForm
from ..services.ticket_service import TicketService
from ..services.eventee_service import EventeeService
from ..services.printing_service import PrintingService
from ..decorators import login_required_ajax, staff_required
from ..utils.error_handlers import handle_view_errors
from ..utils.validators import sanitize_string
from ..utils.auth_utils import get_username_for_log


@login_required_ajax
@handle_view_errors
def ticket_list(request, event_pk):
    """List tickets with search and filtering."""
    event = get_object_or_404(Event, pk=event_pk)
    search_query = sanitize_string(request.GET.get('search', ''))
    status_filter = sanitize_string(request.GET.get('status', ''))

    # Get tickets using service
    tickets = TicketService.search_tickets(search_query, status_filter, event=event)

    # Pagination
    paginator = Paginator(tickets, 25)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)

    # Get statistics
    stats = TicketService.get_statistics(event=event)

    # Check for import errors in session
    import_errors = request.session.get('import_errors', None)
    import_session_key = request.session.get('import_session_key', None)
    import_mode = request.session.get('import_mode', None)
    import_field_mapping = request.session.get('import_field_mapping', None)

    # Clear import data from session after reading
    if import_errors:
        request.session.pop('import_errors', None)
        request.session.pop('import_session_key', None)
        request.session.pop('import_mode', None)
        request.session.pop('import_field_mapping', None)

    context = {
        'event': event,
        'tickets': tickets_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': stats['total'],
        'valid_count': stats['valid'],
        'used_count': stats['used'],
        'import_errors': import_errors,
        'import_session_key': import_session_key,
        'import_mode': import_mode,
        'import_field_mapping': import_field_mapping,
    }

    # Return partial template for AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'tickets/_ticket_table.html', context)

    return render(request, 'tickets/ticket_list.html', context)


@login_required_ajax
@handle_view_errors
def ticket_detail(request, event_pk, pk):
    """View ticket details by ID."""
    event = get_object_or_404(Event, pk=event_pk)
    ticket = get_object_or_404(
        Ticket.objects.select_related().prefetch_related('checkin_set').filter(event=event),
        pk=pk
    )
    return render(request, 'tickets/ticket_detail.html', {'event': event, 'ticket': ticket})


@login_required_ajax
@handle_view_errors
def ticket_detail_by_qr(request, event_pk):
    """View ticket details by QR code."""
    event = get_object_or_404(Event, pk=event_pk)
    qr_code = sanitize_string(request.GET.get('qr_code', ''))

    if not qr_code:
        messages.error(request, 'QR code is required')
        return redirect('tickets:ticket_list', event_pk=event_pk)

    ticket = TicketService.get_ticket_by_qr(qr_code)
    if not ticket:
        messages.error(request, 'Ticket not found')
        return redirect('tickets:ticket_list', event_pk=event_pk)

    return render(request, 'tickets/ticket_detail.html', {'event': event, 'ticket': ticket})


@staff_required
@handle_view_errors
@transaction.atomic
def ticket_create(request, event_pk):
    """Create a new ticket."""
    event = get_object_or_404(Event, pk=event_pk)
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.event = event
            ticket.save()

            # Handle Eventee invitation
            if form.cleaned_data.get('invite_to_eventee') and ticket.email:
                eventee_service = EventeeService(event=event)
                success, message = eventee_service.invite_attendee(
                    email=ticket.email,
                    name=ticket.name,
                    company=ticket.company_name
                )

                if success:
                    ticket.invited = True
                    ticket.save()
                    messages.success(request, f'Ticket created and {message}')
                else:
                    messages.warning(request, f'Ticket created but Eventee invitation failed: {message}')
            else:
                messages.success(request, 'Ticket created successfully')

            Log.objects.create(
                ticket=ticket,
                event=event,
                event_type='CREATE',
                message=f'Ticket created by {get_username_for_log(request)}'
            )

            return redirect('tickets:ticket_detail', event_pk=event_pk, pk=ticket.pk)
    else:
        form = TicketForm()

    return render(request, 'tickets/ticket_form.html', {
        'event': event,
        'form': form,
        'title': 'Create Ticket',
        'button_text': 'Create Ticket'
    })


@staff_required
@handle_view_errors
@transaction.atomic
def ticket_edit(request, event_pk, pk):
    """Edit an existing ticket."""
    event = get_object_or_404(Event, pk=event_pk)
    ticket = get_object_or_404(Ticket, pk=pk, event=event)

    # Store original values for comparison
    original_values = {
        'name': ticket.name,
        'company_name': ticket.company_name,
        'email': ticket.email,
        'event_name': ticket.event.name if ticket.event else '',
        'qr_code': ticket.qr_code,
        'status': ticket.status,
        'gdpr': ticket.gdpr,
    }

    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save()

            # Track changes
            changes = []
            for field, original_value in original_values.items():
                new_value = getattr(ticket, field)
                if str(original_value or '') != str(new_value or ''):
                    changes.append(f'{field}: "{original_value}" → "{new_value}"')

            # Handle Eventee invitation
            if form.cleaned_data.get('invite_to_eventee') and ticket.email and not ticket.invited:
                eventee_service = EventeeService(event=event)
                success, message = eventee_service.invite_attendee(
                    email=ticket.email,
                    name=ticket.name,
                    company=ticket.company_name
                )

                if success:
                    ticket.invited = True
                    ticket.save()
                    changes.append('Invited to Eventee')
                    messages.success(request, f'Ticket updated and {message}')
                else:
                    messages.warning(request, f'Ticket updated but Eventee invitation failed: {message}')
            else:
                messages.success(request, 'Ticket updated successfully')

            # Create detailed log entry
            if changes:
                change_summary = '; '.join(changes)
                log_message = f'Ticket updated by {get_username_for_log(request)}. Changes: {change_summary}'
            else:
                log_message = f'Ticket updated by {get_username_for_log(request)} (no changes detected)'

            Log.objects.create(
                ticket=ticket,
                event=event,
                event_type='UPDATE',
                message=log_message
            )

            return redirect('tickets:ticket_detail', event_pk=event_pk, pk=ticket.pk)
    else:
        form = TicketForm(instance=ticket)

    return render(request, 'tickets/ticket_form.html', {
        'event': event,
        'form': form,
        'ticket': ticket,
        'title': 'Edit Ticket',
        'button_text': 'Save Changes'
    })


@staff_required
@handle_view_errors
@transaction.atomic
def ticket_delete(request, event_pk, pk):
    """Delete a ticket."""
    event = get_object_or_404(Event, pk=event_pk)
    ticket = get_object_or_404(Ticket, pk=pk, event=event)

    if request.method == 'POST':
        Log.objects.create(
            ticket_qr=ticket.qr_code,
            event=event,
            event_type='DELETE',
            message=f'Ticket deleted by {get_username_for_log(request)}: {ticket.name}'
        )
        ticket.delete()
        messages.success(request, 'Ticket deleted successfully')
        return redirect('tickets:ticket_list', event_pk=event_pk)

    return render(request, 'tickets/ticket_confirm_delete.html', {'event': event, 'ticket': ticket})


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def reset_ticket_status(request, event_pk):
    """Reset multiple tickets to VALID status."""
    event = get_object_or_404(Event, pk=event_pk)
    ticket_ids = request.POST.getlist('ticket_ids')

    if not ticket_ids:
        messages.error(request, 'No tickets selected')
        return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_list'))

    with transaction.atomic():
        tickets = Ticket.objects.filter(event=event, id__in=ticket_ids)

        # Create individual log entries for each ticket before resetting
        for ticket in tickets:
            if ticket.status != 'VALID':  # Only log if status is actually changing
                Log.objects.create(
                    ticket=ticket,  # Use ticket reference to link to ticket
                    ticket_qr=ticket.qr_code,  # Also store QR code for reference
                    event=event,
                    event_type='UPDATE',
                    message=f'Ticket reset to VALID status by {get_username_for_log(request)} (was {ticket.get_status_display()})'
                )

        # Get ticket info before update for logging
        ticket_info = []
        for ticket in tickets:
            if ticket.status != 'VALID':
                ticket_info.append(f"{ticket.qr_code} ({ticket.name})")

        count = tickets.update(status='VALID')

        # Delete associated check-ins
        CheckIn.objects.filter(ticket__in=tickets).delete()

        # Create summary log entry with ticket details
        if ticket_info:
            if len(ticket_info) <= 3:
                ticket_list = ", ".join(ticket_info)
            else:
                ticket_list = f"{', '.join(ticket_info[:3])}, and {len(ticket_info) - 3} more"

            Log.objects.create(
                event=event,
                event_type='SYSTEM',
                message=f'{count} ticket(s) reset to VALID status by {get_username_for_log(request)}: {ticket_list}'
            )
        else:
            Log.objects.create(
                event=event,
                event_type='SYSTEM',
                message=f'No tickets needed resetting (all were already VALID) by {get_username_for_log(request)}'
            )

    messages.success(request, f'{count} ticket(s) reset successfully')

    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'{count} tickets reset successfully'
        })

    # Otherwise redirect back to the referring page
    return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_list'))


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def delete_tickets(request, event_pk):
    """Delete multiple tickets."""
    event = get_object_or_404(Event, pk=event_pk)
    ticket_ids = request.POST.getlist('ticket_ids')

    if not ticket_ids:
        return JsonResponse({
            'success': False,
            'message': 'No tickets selected'
        })

    with transaction.atomic():
        tickets = Ticket.objects.filter(event=event, id__in=ticket_ids)
        count = tickets.count()

        # Log before deletion
        for ticket in tickets:
            Log.objects.create(
                ticket_qr=ticket.qr_code,
                event=event,
                event_type='DELETE',
                message=f'Ticket deleted by {get_username_for_log(request)}: {ticket.name}'
            )

        tickets.delete()

    return JsonResponse({
        'success': True,
        'message': f'{count} tickets deleted successfully'
    })


@login_required_ajax
def export_tickets_csv(request, event_pk):
    """Export tickets to CSV with detailed check-in information."""
    from django.utils import timezone

    event = get_object_or_404(Event, pk=event_pk)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'event_checkins_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Add BOM for Excel UTF-8 compatibility
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'QR Code', 'Name', 'Company', 'Email', 'Event', 'Status',
        'Check-in Time', 'Check-in Count', 'Invited to Eventee', 'Created At'
    ])

    tickets = Ticket.objects.filter(event=event).select_related().prefetch_related('checkin_set').order_by('name')

    stats = {
        'total': 0,
        'checked_in': 0,
        'not_checked_in': 0
    }

    for ticket in tickets:
        stats['total'] += 1
        checkin = ticket.checkin_set.first()

        if checkin:
            stats['checked_in'] += 1
            checkin_time = checkin.check_in_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            stats['not_checked_in'] += 1
            checkin_time = ''

        writer.writerow([
            ticket.qr_code,
            ticket.name,
            ticket.company_name or '',
            ticket.email or '',
            (ticket.event.name if ticket.event else ''),
            ticket.get_status_display(),
            checkin_time,
            ticket.checkin_set.count(),
            'Yes' if ticket.invited else 'No',
            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    # Add summary at the end
    writer.writerow([])  # Empty row
    writer.writerow(['SUMMARY', '', '', '', '', '', '', '', '', ''])
    writer.writerow(['Total Tickets:', stats['total'], '', '', '', '', '', '', '', ''])
    writer.writerow(['Checked In:', stats['checked_in'], '', '', '', '', '', '', '', ''])
    writer.writerow(['Not Checked In:', stats['not_checked_in'], '', '', '', '', '', '', '', ''])
    writer.writerow(['Check-in Rate:', f"{(stats['checked_in'] / stats['total'] * 100):.1f}%" if stats['total'] > 0 else '0%', '', '', '', '', '', '', '', ''])

    # Log the export
    Log.objects.create(
        event=event,
        event_type='SYSTEM',
        message=f'Check-in report exported by {get_username_for_log(request)} - {stats["checked_in"]}/{stats["total"]} checked in'
    )

    return response


@login_required_ajax
def export_tickets_xlsx(request, event_pk):
    """Export all tickets to XLSX. Uses openpyxl; avoids N+1 via prefetch cache."""
    import io
    from django.utils import timezone
    from openpyxl import Workbook
    from openpyxl.styles import Font

    event = get_object_or_404(Event, pk=event_pk)

    tickets = Ticket.objects.filter(event=event).select_related().prefetch_related('checkin_set').order_by('name')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Tickets'

    headers = [
        'QR Code', 'Name', 'Company', 'Email', 'Event', 'Status',
        'Check-in Time', 'Check-in Count', 'Invited to Eventee', 'Created At',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    stats = {'total': 0, 'checked_in': 0, 'not_checked_in': 0}

    for ticket in tickets:
        stats['total'] += 1
        checkins = list(ticket.checkin_set.all())  # reads from prefetch cache once
        checkin = checkins[0] if checkins else None
        if checkin:
            stats['checked_in'] += 1
            checkin_time = checkin.check_in_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            stats['not_checked_in'] += 1
            checkin_time = ''

        ws.append([
            ticket.qr_code,
            ticket.name,
            ticket.company_name or '',
            ticket.email or '',
            (ticket.event.name if ticket.event else ''),
            ticket.get_status_display(),
            checkin_time,
            len(checkins),
            'Yes' if ticket.invited else 'No',
            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    # Auto-width columns
    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = max_len + 2

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    Log.objects.create(
        event=event,
        event_type='SYSTEM',
        message=(
            f'XLSX report exported by {get_username_for_log(request)} — '
            f'{stats["checked_in"]}/{stats["total"]} checked in'
        )
    )

    filename = f'event_checkins_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
