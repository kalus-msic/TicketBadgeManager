import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from ..models import Ticket, Log, CheckIn
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
def ticket_list(request):
    """List tickets with search and filtering."""
    search_query = sanitize_string(request.GET.get('search', ''))
    status_filter = sanitize_string(request.GET.get('status', ''))
    
    # Get tickets using service
    tickets = TicketService.search_tickets(search_query, status_filter)
    
    # Pagination
    paginator = Paginator(tickets, 25)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)
    
    # Get statistics
    stats = TicketService.get_statistics()
    
    context = {
        'tickets': tickets_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': stats['total'],
        'valid_count': stats['valid'],
        'used_count': stats['used'],
    }
    
    # Return partial template for AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'tickets/_ticket_table.html', context)
    
    return render(request, 'tickets/ticket_list.html', context)


@login_required_ajax
@handle_view_errors
def ticket_detail(request, pk):
    """View ticket details by ID."""
    ticket = get_object_or_404(
        Ticket.objects.select_related().prefetch_related('checkin_set'),
        pk=pk
    )
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})


@login_required_ajax
@handle_view_errors
def ticket_detail_by_qr(request):
    """View ticket details by QR code."""
    qr_code = sanitize_string(request.GET.get('qr_code', ''))
    
    if not qr_code:
        messages.error(request, 'QR code is required')
        return redirect('tickets:ticket_list')
    
    ticket = TicketService.get_ticket_by_qr(qr_code)
    if not ticket:
        messages.error(request, 'Ticket not found')
        return redirect('tickets:ticket_list')
    
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})


@staff_required
@handle_view_errors
@transaction.atomic
def ticket_create(request):
    """Create a new ticket."""
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save()
            
            # Handle Eventee invitation
            if form.cleaned_data.get('invite_to_eventee') and ticket.email:
                eventee_service = EventeeService()
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
                event_type='UPDATE',
                message=f'Ticket created by {get_username_for_log(request)}'
            )
            
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'title': 'Create Ticket',
        'button_text': 'Create Ticket'
    })


@staff_required
@handle_view_errors
@transaction.atomic
def ticket_edit(request, pk):
    """Edit an existing ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Store original values for comparison
    original_values = {
        'name': ticket.name,
        'company_name': ticket.company_name,
        'email': ticket.email,
        'event_name': ticket.event_name,
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
                eventee_service = EventeeService()
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
                event_type='UPDATE',
                message=log_message
            )
            
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(instance=ticket)
    
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'ticket': ticket,
        'title': 'Edit Ticket',
        'button_text': 'Save Changes'
    })


@staff_required
@handle_view_errors
@transaction.atomic
def ticket_delete(request, pk):
    """Delete a ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        Log.objects.create(
            ticket_qr=ticket.qr_code,
            event_type='UPDATE',
            message=f'Ticket deleted by {request.user.username}: {ticket.name}'
        )
        ticket.delete()
        messages.success(request, 'Ticket deleted successfully')
        return redirect('tickets:ticket_list')
    
    return render(request, 'tickets/ticket_confirm_delete.html', {'ticket': ticket})


@staff_required
@require_http_methods(['POST'])
@handle_view_errors
def reset_ticket_status(request):
    """Reset multiple tickets to VALID status."""
    ticket_ids = request.POST.getlist('ticket_ids')
    
    if not ticket_ids:
        messages.error(request, 'No tickets selected')
        return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_list'))
    
    with transaction.atomic():
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        
        # Create individual log entries for each ticket before resetting
        for ticket in tickets:
            if ticket.status != 'VALID':  # Only log if status is actually changing
                Log.objects.create(
                    ticket_qr=ticket.qr_code,  # Use only ticket_qr, not ticket reference
                    event_type='UPDATE',
                    message=f'Ticket reset to VALID status by {get_username_for_log(request)} (was {ticket.get_status_display()})'
                )
        
        count = tickets.update(status='VALID')
        
        # Delete associated check-ins
        CheckIn.objects.filter(ticket__in=tickets).delete()
        
        # Create summary log entry
        Log.objects.create(
            event_type='SYSTEM',
            message=f'{count} tickets reset to VALID status by {get_username_for_log(request)}'
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
def delete_tickets(request):
    """Delete multiple tickets."""
    ticket_ids = request.POST.getlist('ticket_ids')
    
    if not ticket_ids:
        return JsonResponse({
            'success': False,
            'message': 'No tickets selected'
        })
    
    with transaction.atomic():
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        count = tickets.count()
        
        # Log before deletion
        for ticket in tickets:
            Log.objects.create(
                ticket_qr=ticket.qr_code,
                event_type='UPDATE',
                message=f'Ticket deleted by {request.user.username}: {ticket.name}'
            )
        
        tickets.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'{count} tickets deleted successfully'
    })


@login_required_ajax
def export_tickets_csv(request):
    """Export tickets to CSV with detailed check-in information."""
    from django.utils import timezone
    
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
    
    tickets = Ticket.objects.select_related().prefetch_related('checkin_set').order_by('name')
    
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
            ticket.event_name or '',
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
        event_type='SYSTEM',
        message=f'Check-in report exported by {get_username_for_log(request)} - {stats["checked_in"]}/{stats["total"]} checked in'
    )
    
    return response