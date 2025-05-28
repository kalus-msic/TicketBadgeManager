from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from ..models import Ticket, Log
from ..forms import CsvImportForm
from ..services.ticket_service import TicketService
from ..decorators import staff_required, import_ratelimit
from ..utils.error_handlers import handle_view_errors
from ..utils.validators import validate_csv_file
from ..utils.auth_utils import get_username_for_log


@staff_required
def import_page(request):
    """Display import page."""
    form = CsvImportForm()
    return render(request, 'tickets/import.html', {
        'form': form,
        'current_ticket_count': Ticket.objects.count()
    })


@staff_required
@import_ratelimit
@handle_view_errors
def import_replace_tickets(request):
    """Import CSV and replace all existing tickets."""
    if request.method == 'POST':
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Validate file
            validate_csv_file(csv_file)
            
            # Read file content
            file_content = csv_file.read().decode('utf-8-sig')
            
            # Import using service
            results = TicketService.import_tickets_from_csv(file_content, replace_existing=True)
            
            messages.success(
                request,
                f"Successfully imported {results['imported']} tickets. "
                f"{results['errors']} rows had errors."
            )
            
            Log.objects.create(
                event_type='SYSTEM',
                message=f"CSV import (replace) by {get_username_for_log(request)}: "
                       f"{results['imported']} imported, {results['errors']} errors"
            )
    
    return redirect('tickets:import_page')


@staff_required
@import_ratelimit
@handle_view_errors
def import_add_tickets(request):
    """Import CSV and add to existing tickets."""
    if request.method == 'POST':
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Validate file
            validate_csv_file(csv_file)
            
            # Read file content
            file_content = csv_file.read().decode('utf-8-sig')
            
            # Import using service
            results = TicketService.import_tickets_from_csv(file_content, replace_existing=False)
            
            messages.success(
                request,
                f"Successfully imported {results['imported']} tickets. "
                f"{results['duplicates']} duplicates skipped, "
                f"{results['errors']} rows had errors."
            )
            
            Log.objects.create(
                event_type='SYSTEM',
                message=f"CSV import (add) by {get_username_for_log(request)}: "
                       f"{results['imported']} imported, {results['duplicates']} duplicates, "
                       f"{results['errors']} errors"
            )
    
    return redirect('tickets:import_page')


@staff_required
def merge_import(request):
    """Prepare import with merge options."""
    return render(request, 'tickets/prepare_import.html')