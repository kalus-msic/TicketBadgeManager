from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.cache import cache
from django.http import JsonResponse
import csv
import io
import uuid
from ..models import Ticket, Log
from ..forms import CsvImportForm
from ..services.ticket_service import TicketService
from ..decorators import staff_required, import_ratelimit
from ..utils.error_handlers import handle_view_errors
from ..utils.validators import validate_csv_file
from ..utils.auth_utils import get_username_for_log
from ..utils.import_mappings import get_field_mapping_suggestions, detect_import_profile, IMPORT_PROFILES


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
                event_type='IMPORT',
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
                event_type='IMPORT',
                message=f"CSV import (add) by {get_username_for_log(request)}: "
                       f"{results['imported']} imported, {results['duplicates']} duplicates, "
                       f"{results['errors']} errors"
            )
    
    return redirect('tickets:import_page')


@staff_required
def merge_import(request):
    """Prepare import with merge options."""
    return render(request, 'tickets/prepare_import.html')


@staff_required
@handle_view_errors
def import_mapping(request):
    """Handle CSV upload and show column mapping interface."""
    if request.method == 'POST' and 'csv_file' in request.FILES:
        csv_file = request.FILES['csv_file']
        
        # Validate file
        validate_csv_file(csv_file)
        
        # Read and parse CSV
        file_content = csv_file.read().decode('utf-8-sig')
        
        # Try to detect delimiter
        try:
            # Use csv.Sniffer to detect delimiter
            sample = file_content[:1024]  # First 1KB for detection
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
            delimiter = dialect.delimiter
        except:
            # Default to comma if detection fails
            delimiter = ','
        
        # Try parsing with detected delimiter
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)
        
        # Get column names and sample data
        rows = list(csv_reader)
        if not rows:
            messages.error(request, "CSV file is empty")
            return redirect('tickets:import_page')
        
        # If we only got one column, try the other delimiter
        if len(csv_reader.fieldnames) == 1 and delimiter == ',':
            # Try semicolon
            file_content_io = io.StringIO(file_content)
            csv_reader = csv.DictReader(file_content_io, delimiter=';')
            rows = list(csv_reader)
            delimiter = ';'
        elif len(csv_reader.fieldnames) == 1 and delimiter == ';':
            # Try comma
            file_content_io = io.StringIO(file_content)
            csv_reader = csv.DictReader(file_content_io, delimiter=',')
            rows = list(csv_reader)
            delimiter = ','
        
        # Get field mapping suggestions using the new system
        suggestions = get_field_mapping_suggestions(csv_reader.fieldnames, 
                                                     samples={field: [row.get(field) for row in rows[:3] if row.get(field)] 
                                                             for field in csv_reader.fieldnames})
        
        # Detect import profile
        detected_profile = detect_import_profile(csv_reader.fieldnames)
        
        columns = []
        for field in csv_reader.fieldnames:
            # Get sample values (up to 3)
            samples = []
            for i, row in enumerate(rows[:3]):
                if row.get(field):
                    samples.append(row[field])
            
            columns.append({
                'name': field,
                'samples': samples,
                'suggested_field': suggestions.get(field)
            })
        
        # Store CSV data in cache for processing
        session_key = str(uuid.uuid4())
        cache.set(f'import_{session_key}', {
            'fieldnames': csv_reader.fieldnames,
            'rows': rows,
            'filename': csv_file.name,
            'delimiter': delimiter
        }, 3600)  # Cache for 1 hour
        
        context = {
            'csv_columns': columns,
            'total_rows': len(rows),
            'session_key': session_key,
            'delimiter': delimiter,
            'delimiter_name': 'comma' if delimiter == ',' else 
                            'semicolon' if delimiter == ';' else
                            'tab' if delimiter == '\t' else
                            'pipe' if delimiter == '|' else 'other',
            'detected_profile': detected_profile,
            'profile_name': IMPORT_PROFILES.get(detected_profile, {}).get('name', 'Unknown')
        }
        
        return render(request, 'tickets/import_mapping.html', context)
    
    return redirect('tickets:import_page')


def _suggest_field_mapping(column_name, samples):
    """Try to guess the appropriate field mapping based on column name and data."""
    column_lower = column_name.lower().strip()
    
    # QR Code patterns
    if any(x in column_lower for x in ['qr', 'code', 'ticket', 'unique']):
        return 'qr_code'
    
    # Email patterns
    if 'email' in column_lower or 'mail' in column_lower:
        return 'email'
    elif samples and '@' in str(samples[0]):
        return 'email'
    
    # Name patterns
    if any(x in column_lower for x in ['first', 'given', 'forename']):
        return 'name'
    elif column_lower in ['name', 'jméno', 'meno']:
        return 'name'
    
    # Last name patterns
    if any(x in column_lower for x in ['last', 'surname', 'family']):
        return 'last_name'
    elif column_lower in ['příjmení', 'priezvisko']:
        return 'last_name'
    
    # Company patterns
    if any(x in column_lower for x in ['company', 'firma', 'organization', 'org']):
        return 'company_name'
    
    # Event patterns
    if any(x in column_lower for x in ['event', 'akce', 'událost']):
        return 'event_name'
    
    return None


@staff_required
@import_ratelimit
@handle_view_errors
def import_execute(request):
    """Execute the import with user-defined mapping."""
    if request.method != 'POST':
        return redirect('tickets:import_page')
    
    session_key = request.POST.get('session_key')
    import_mode = request.POST.get('import_mode', 'replace')
    force_import = request.POST.get('force_import', 'false') == 'true'
    
    # Get cached CSV data
    csv_data = cache.get(f'import_{session_key}')
    if not csv_data:
        messages.error(request, "Import session expired. Please upload the file again.")
        return redirect('tickets:import_page')
    
    # Build field mapping
    field_mapping = {}
    for i, fieldname in enumerate(csv_data['fieldnames']):
        mapping_value = request.POST.get(f'mapping_{i}')
        if mapping_value:
            field_mapping[fieldname] = mapping_value
    
    # Validate required fields
    if 'qr_code' not in field_mapping.values():
        messages.error(request, "QR Code field mapping is required")
        return redirect('tickets:import_page')
    
    if 'name' not in field_mapping.values():
        messages.error(request, "Name field mapping is required")
        return redirect('tickets:import_page')
    
    # Process import
    imported = 0
    errors = 0
    duplicates = 0
    updated = 0
    error_details = []  # Store error details for logging
    
    # Handle replace mode first (outside of row processing)
    if import_mode == 'replace':
        old_count = Ticket.objects.count()
        Ticket.objects.all().delete()
        Log.objects.create(
            event_type='DELETE',
            message=f"Deleted {old_count} tickets before import (replace mode) by {get_username_for_log(request)}"
        )
    
    # Process each row individually (not in atomic transaction)
    for row_num, row in enumerate(csv_data['rows'], start=2):
        try:
            with transaction.atomic():
                # Map fields according to user mapping
                ticket_data = {}
                for csv_field, model_field in field_mapping.items():
                    value = row.get(csv_field, '').strip()
                    if value:
                        # Special handling for QR code - extract from URL if needed
                        if model_field == 'qr_code':
                            from ..utils.text_utils import extract_qr_from_url
                            value = extract_qr_from_url(value)
                        ticket_data[model_field] = value
                
                # Check if ticket exists (by QR code)
                qr_code = ticket_data.get('qr_code')
                if not qr_code:
                    if force_import:
                        # Generate a placeholder QR code
                        from django.utils import timezone
                        qr_code = f"MISSING_QR_{timezone.now().strftime('%Y%m%d%H%M%S')}_{row_num}"
                        ticket_data['qr_code'] = qr_code
                    else:
                        errors += 1
                        error_details.append(f"Row {row_num}: Missing QR code")
                        continue
                
                # Check if name exists
                if not ticket_data.get('name'):
                    if force_import:
                        # Use a placeholder name
                        ticket_data['name'] = f"Missing Name (Row {row_num})"
                    else:
                        errors += 1
                        error_details.append(f"Row {row_num}: Missing name (QR: {qr_code})")
                        continue
                
                existing_ticket = Ticket.objects.filter(qr_code=qr_code).first()
                
                if import_mode == 'append' and existing_ticket:
                    duplicates += 1
                    continue
                elif import_mode == 'update' and existing_ticket:
                    # Update existing ticket
                    for field, value in ticket_data.items():
                        if field != 'qr_code':  # Don't update QR code
                            setattr(existing_ticket, field, value)
                    existing_ticket.save()
                    updated += 1
                else:
                    # Create new ticket
                    # Combine name and last_name if both exist
                    if 'last_name' in ticket_data and 'name' in ticket_data:
                        full_name = f"{ticket_data['name']} {ticket_data['last_name']}"
                        ticket_data['name'] = full_name
                        del ticket_data['last_name']
                    
                    Ticket.objects.create(**ticket_data)
                    imported += 1
                    
        except Exception as e:
            if force_import and "UNIQUE constraint failed" in str(e):
                # Handle duplicate QR code in force mode
                try:
                    # Generate alternative QR code
                    original_qr = ticket_data.get('qr_code', '')
                    ticket_data['qr_code'] = f"{original_qr}_DUP_{row_num}"
                    
                    # Try again with modified QR
                    if import_mode == 'update' and existing_ticket:
                        for field, value in ticket_data.items():
                            if field != 'qr_code':
                                setattr(existing_ticket, field, value)
                        existing_ticket.save()
                        updated += 1
                    else:
                        # Combine name and last_name if both exist
                        if 'last_name' in ticket_data and 'name' in ticket_data:
                            full_name = f"{ticket_data['name']} {ticket_data['last_name']}"
                            ticket_data['name'] = full_name
                            del ticket_data['last_name']
                        
                        Ticket.objects.create(**ticket_data)
                        imported += 1
                except Exception as e2:
                    errors += 1
                    error_details.append(f"Row {row_num}: {str(e2)} (QR: {ticket_data.get('qr_code', 'N/A')})")
            else:
                errors += 1
                error_details.append(f"Row {row_num}: {str(e)} (QR: {ticket_data.get('qr_code', 'N/A')})")
    
    # Clear cache
    cache.delete(f'import_{session_key}')
    
    # Create main log entry
    log_message = f"CSV import ({import_mode}) by {get_username_for_log(request)}: "
    log_message += f"{imported} imported, {updated} updated, {duplicates} duplicates, {errors} errors"
    
    # Add error details to log if any
    if error_details:
        log_message += "\n\nError details:\n" + "\n".join(error_details[:20])  # Limit to first 20 errors
        if len(error_details) > 20:
            log_message += f"\n... and {len(error_details) - 20} more errors"
    
    Log.objects.create(
        event_type='IMPORT',
        message=log_message
    )
    
    # Show results with error details
    if errors > 0 and not force_import:
        # Store error details and import data in session for possible retry
        request.session['import_errors'] = error_details
        request.session['import_session_key'] = session_key
        request.session['import_mode'] = import_mode
        
        # Store mapping with indices for form reconstruction
        indexed_mapping = {}
        for i, fieldname in enumerate(csv_data['fieldnames']):
            if fieldname in field_mapping:
                indexed_mapping[i] = field_mapping[fieldname]
        request.session['import_field_mapping'] = indexed_mapping
        
        # Re-cache the data for a bit longer to allow retry
        cache.set(f'import_{session_key}', csv_data, 300)  # Keep for 5 more minutes
    else:
        # Clear any previous import session data
        request.session.pop('import_errors', None)
        request.session.pop('import_session_key', None)
        request.session.pop('import_mode', None)
        request.session.pop('import_field_mapping', None)
        
    if import_mode == 'replace':
        if errors > 0 and not force_import:
            messages.warning(request, f"Imported {imported} tickets. {errors} rows had errors. You can force import these rows if needed.")
        elif force_import and imported > 0:
            messages.success(request, f"Force imported {imported} tickets with placeholders for missing data.")
        else:
            messages.success(request, f"Successfully imported {imported} tickets.")
    elif import_mode == 'append':
        if errors > 0 and not force_import:
            messages.warning(request, f"Imported {imported} new tickets. "
                                    f"{duplicates} duplicates skipped, {errors} rows had errors. You can force import these rows if needed.")
        elif force_import and imported > 0:
            messages.success(request, f"Force imported {imported} new tickets with placeholders. {duplicates} duplicates skipped.")
        else:
            messages.success(request, f"Successfully imported {imported} new tickets. "
                                    f"{duplicates} duplicates skipped.")
    else:  # update
        if errors > 0 and not force_import:
            messages.warning(request, f"Imported {imported} new tickets and updated {updated} existing ones. "
                                    f"{errors} rows had errors. You can force import these rows if needed.")
        elif force_import and (imported > 0 or updated > 0):
            messages.success(request, f"Force imported {imported} new tickets and updated {updated} existing ones with placeholders.")
        else:
            messages.success(request, f"Successfully imported {imported} new tickets and updated {updated} existing ones.")
    
    return redirect('tickets:ticket_list')


@staff_required
def import_preview(request):
    """AJAX endpoint to preview import results."""
    session_key = request.GET.get('session_key')
    import_mode = request.GET.get('import_mode', 'replace')
    
    # Get cached CSV data
    csv_data = cache.get(f'import_{session_key}')
    if not csv_data:
        return JsonResponse({'error': 'Session expired'}, status=400)
    
    # Build field mapping from request
    field_mapping = {}
    for key, value in request.GET.items():
        if key.startswith('mapping_'):
            idx = int(key.replace('mapping_', ''))
            if idx < len(csv_data['fieldnames']) and value:
                field_mapping[csv_data['fieldnames'][idx]] = value
    
    # Preview first 5 rows
    preview_data = []
    for row in csv_data['rows'][:5]:
        mapped_row = {}
        for csv_field, model_field in field_mapping.items():
            value = row.get(csv_field, '')
            if value:
                mapped_row[model_field] = value
        
        # Check if would be duplicate
        if 'qr_code' in mapped_row:
            existing = Ticket.objects.filter(qr_code=mapped_row['qr_code']).exists()
            mapped_row['_exists'] = existing
            mapped_row['_action'] = 'skip' if (import_mode == 'append' and existing) else \
                                   'update' if (import_mode == 'update' and existing) else \
                                   'create'
        
        preview_data.append(mapped_row)
    
    return JsonResponse({
        'preview': preview_data,
        'total_existing': Ticket.objects.filter(
            qr_code__in=[r.get(field_mapping.get('qr_code', ''), '') for r in csv_data['rows']]
        ).count()
    })