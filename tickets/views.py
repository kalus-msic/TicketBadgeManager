
import csv
from io import TextIOWrapper
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Ticket, CheckIn
from .forms import CsvImportForm, TicketForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
import pandas as pd
from django.http import HttpResponse
from django.core.files.storage import default_storage
import os
from django.views.decorators.http import require_POST
import datetime
import random
import ctypes
from PIL import Image, ImageDraw, ImageFont
import textwrap
import numpy as np

import platform
if platform.system() == "Windows":
    import win32print
else:
    print("win32print is not available on this platform.")

def index(request):
    # Get counts for statistics
    total_tickets = Ticket.objects.count()
    valid_tickets = Ticket.objects.filter(status='VALID').count()
    used_tickets = Ticket.objects.filter(status='USED').count()
    total_checkins = CheckIn.objects.count()
    
    # Get recent check-ins
    recent_checkins = CheckIn.objects.select_related('ticket').order_by('-check_in_time')[:10]
    
    context = {
        'total_tickets': total_tickets,
        'valid_tickets': valid_tickets,
        'used_tickets': used_tickets,
        'total_checkins': total_checkins,
        'recent_checkins': recent_checkins,
    }
    return render(request, 'tickets/index.html', context)

def ticket_list(request):
    # Get search parameter
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    tickets = Ticket.objects.all().order_by('-created_at')
    
    # Apply search
    if search_query:
        tickets = tickets.filter(
            Q(name__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(qr_code__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter and status_filter != 'ALL':
        tickets = tickets.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(tickets, 25)  # 25 tickets per page
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)
    
    context = {
        'tickets': tickets_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': Ticket.objects.count(),
        'valid_count': Ticket.objects.filter(status='VALID').count(),
        'used_count': Ticket.objects.filter(status='USED').count(),
    }
    return render(request, 'tickets/ticket_list.html', context)


def detect_delimiter(file_content):
    """Detect if the CSV uses comma or semicolon as delimiter."""
    first_line = file_content.splitlines()[0]
    if ';' in first_line:
        return ';'
    return ','

def import_page(request):
    """View to render the import page with both options"""
    form = CsvImportForm()
    return render(request, 'tickets/import.html', {
        'form': form,
        'current_ticket_count': Ticket.objects.count()
    })

def import_replace_tickets(request):
    """Delete all existing data and import new tickets"""
    if request.method == 'POST':
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Read the file content to detect delimiter
                file_content = request.FILES['csv_file'].read().decode('utf-8-sig')
                delimiter = ';' if ';' in file_content.splitlines()[0] else ','
                
                # Create a CSV reader from the content
                reader = csv.DictReader(file_content.splitlines(), delimiter=delimiter)
                
                print(f"Found CSV columns: {reader.fieldnames}")
                print(f"Using delimiter: {delimiter}")
                
                imported_count = 0
                error_count = 0
                
                with transaction.atomic():
                    # Delete ALL existing tickets (and related check-ins)
                    Ticket.objects.all().delete()
                    
                    # Import new data
                    for row in reader:
                        try:
                            qr_code = (
                                row.get('Číslo vstupenky') or 
                                row.get('Ticket Number') or
                                row.get('Ticket Reference')
                            )
                            
                            first_name = (
                                row.get('Jméno') or
                                row.get('Jméno_x') or 
                                row.get('Ticket First Name')
                            )
                            last_name = (
                                row.get('Příjmení') or
                                row.get('Příjmení_x') or
                                row.get('Ticket Last Name')
                            )
                            company_name = (
                                row.get('Firma') or 
                                row.get('Field1') or
                                row.get('Ticket Company Name')
                            )
                            event_name = (
                                row.get('Akce_x') or 
                                row.get('Akce') or
                                row.get('Event') 
                            )
                            email = (
                                row.get('Email') or 
                                row.get('E-mail') or
                                row.get('Ticket Email') 
                            )
                            if not all([qr_code, first_name, last_name]):
                                print(f"Skipping row due to missing required fields: {row}")
                                error_count += 1
                                continue
                            
                            name = f"{first_name} {last_name}".strip()
                            qr_code = qr_code.strip()
                            company_name = company_name.strip() if company_name else ''
                            
                            Ticket.objects.create(
                                qr_code=qr_code,
                                name=name,
                                company_name=company_name,
                                event_name=event_name,
                                email=email,
                                status='VALID'
                            )
                            imported_count += 1
                            
                        except Exception as e:
                            print(f"Error processing row: {row}. Error: {str(e)}")
                            error_count += 1
                            continue
                
                messages.success(
                    request, 
                    f'Successfully deleted all existing data and imported {imported_count} new tickets.'
                    f'{" " + str(error_count) + " rows had errors and were skipped." if error_count else ""}'
                )
                
            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')
                print("Import error:", str(e))
                
    return redirect('tickets:import_page')

def import_add_tickets(request):
    """Add new tickets while preserving existing ones"""
    if request.method == 'POST':
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Read the file content to detect delimiter
                file_content = request.FILES['csv_file'].read().decode('utf-8-sig')
                delimiter = ';' if ';' in file_content.splitlines()[0] else ','
                
                # Create a CSV reader from the content
                reader = csv.DictReader(file_content.splitlines(), delimiter=delimiter)
                
                print(f"Found CSV columns: {reader.fieldnames}")
                print(f"Using delimiter: {delimiter}")
                
                imported_count = 0
                error_count = 0
                duplicate_count = 0
                
                with transaction.atomic():
                    existing_qr_codes = set(Ticket.objects.values_list('qr_code', flat=True))
                    
                    for row in reader:
                        try:
                            qr_code = (
                                row.get('Číslo vstupenky') or 
                                row.get('Ticket Number') or
                                row.get('Ticket Reference')
                            )
                            
                            first_name = (
                                row.get('Jméno') or
                                row.get('Jméno_x') or 
                                row.get('Ticket First Name')
                            )
                            last_name = (
                                row.get('Příjmení') or
                                row.get('Příjmení_x') or
                                row.get('Ticket Last Name')
                            )
                            company_name = (
                                row.get('Firma') or 
                                row.get('Field1') or
                                row.get('Ticket Company Name')
                            )
                            event_name = (
                                row.get('Akce_x') or 
                                row.get('Akce') or
                                row.get('Event') 
                            )
                            email = (
                                row.get('Email') or 
                                row.get('E-mail') or
                                row.get('Ticket Email') 
                            )
                            
                            if not all([qr_code, first_name, last_name]):
                                print(f"Skipping row due to missing required fields: {row}")
                                error_count += 1
                                continue
                            
                            name = f"{first_name} {last_name}".strip()
                            qr_code = qr_code.strip()
                            company_name = company_name.strip() if company_name else ''
                            
                            # Check if QR code already exists
                            if qr_code in existing_qr_codes:
                                print(f"Duplicate QR code found: {qr_code}")
                                duplicate_count += 1
                                continue
                            
                            Ticket.objects.create(
                                qr_code=qr_code,
                                name=name,
                                company_name=company_name,
                                event_name=event_name,
                                email=email,
                                status='VALID'
                            )
                            imported_count += 1
                            existing_qr_codes.add(qr_code)  # Add to set to check future duplicates
                            
                        except Exception as e:
                            print(f"Error processing row: {row}. Error: {str(e)}")
                            error_count += 1
                            continue
                
                message_parts = [f'Successfully imported {imported_count} new tickets.']
                if duplicate_count:
                    message_parts.append(f'{duplicate_count} duplicates were skipped.')
                if error_count:
                    message_parts.append(f'{error_count} rows had errors.')
                
                messages.success(request, ' '.join(message_parts))
                
            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')
                print("Import error:", str(e))
                
    return redirect('tickets:import_page')


def scanner_page(request):
    return render(request, 'tickets/scanner.html')

@csrf_exempt
def verify_ticket(request):
    qr_code = request.GET.get('qr_code') if request.method == 'GET' else request.POST.get('qr_code')
    printer_queue = request.GET.get('printer_queue', '1') if request.method == 'GET' else request.POST.get('printer_queue', '1')

    if qr_code:
        try:
            ticket = Ticket.objects.get(qr_code=qr_code)
            if ticket.status == 'VALID':
                CheckIn.objects.create(ticket=ticket)
                ticket.status = 'USED'
                ticket.save()
                
                response = JsonResponse({
                    'valid': True,
                    'message': 'Valid ticket!',
                    'qr_code': ticket.qr_code,
                    'name': ticket.name,
                    'company': ticket.company_name,
                    'event_name': ticket.event_name,
                })
                
                create_label_image(ticket.name, ticket.company_name, ticket.qr_code, printer_queue)
                
                return response
            else:
                return JsonResponse({
                    'valid': False,
                    'message': f'Ticket is already {ticket.status.lower()}!',
                    'qr_code': ticket.qr_code,
                    'name': ticket.name,
                })

        except Ticket.DoesNotExist:
            return JsonResponse({
                'valid': False,
                'message': 'Invalid ticket!'
            })

    # Pokud chybí QR kód, zobrazí se stránka skeneru
    if request.method == 'GET':
        return render(request, 'tickets/scanner.html')

    return JsonResponse({'error': 'Invalid request method'})

def settings(request):
    # Get counts for display
    ticket_count = Ticket.objects.count()
    checkin_count = CheckIn.objects.count()
    
    context = {
        'ticket_count': ticket_count,
        'checkin_count': checkin_count,
    }
    return render(request, 'tickets/settings.html', context)

def delete_all_data(request):
    if request.method == 'POST':
        try:
            # Delete all tickets (this will also delete related check-ins due to CASCADE)
            tickets_count = Ticket.objects.count()
            checkins_count = CheckIn.objects.count()
            Ticket.objects.all().delete()
            messages.success(
                request, 
                f'Successfully deleted all data: {tickets_count} tickets and {checkins_count} check-ins.'
            )
        except Exception as e:
            messages.error(request, f'Error deleting data: {str(e)}')
    return redirect('tickets:settings')

def delete_checkins(request):
    if request.method == 'POST':
        try:
            # Only delete check-ins, keep tickets
            checkins_count = CheckIn.objects.count()
            CheckIn.objects.all().delete()
            # Reset all tickets status to VALID
            Ticket.objects.all().update(status='VALID')
            messages.success(request, f'Successfully deleted {checkins_count} check-ins. All tickets reset to VALID status.')
        except Exception as e:
            messages.error(request, f'Error deleting check-ins: {str(e)}')
    return redirect('tickets:settings')

def merge_import(request):
    if request.method == 'POST' and 'file1' in request.FILES and 'file2' in request.FILES:
        # Save uploaded files temporarily
        file1 = request.FILES['file1']
        file2 = request.FILES['file2']
        file1_path = default_storage.save('temp/' + file1.name, file1)
        file2_path = default_storage.save('temp/' + file2.name, file2)

        # Load Excel files
        df1 = pd.read_excel(file1_path, engine='openpyxl')
        df2 = pd.read_excel(file2_path, engine='openpyxl')

        # Ensure both dataframes have the 'Číslo vstupenky' column
        missing_columns = []
        if 'Číslo vstupenky' not in df1.columns:
            missing_columns.append("File 1 missing 'Číslo vstupenky': " + ", ".join(str(col) for col in df1.columns))
        if 'Číslo vstupenky' not in df2.columns:
            missing_columns.append("File 2 missing 'Číslo vstupenky': " + ", ".join(str(col) for col in df2.columns))

        # If missing, show detailed error log
        if missing_columns:
            error_message = "The required column 'Číslo vstupenky' is missing in one of the files.<br>" + "<br>".join(missing_columns)
            return HttpResponse(error_message, status=400)

        # Ensure matching data types for 'Číslo vstupenky' column
        df1['Číslo vstupenky'] = df1['Číslo vstupenky'].astype(str).str.strip()
        df2['Číslo vstupenky'] = df2['Číslo vstupenky'].astype(str).str.strip()

        # Perform right join merge on 'Číslo vstupenky' (all records from df2)
        merged_df = pd.merge(df1, df2, on='Číslo vstupenky', how='right')

        # Save the merged dataframe to a CSV file with semicolon delimiter
        output_path = 'temp/merged_file.csv'
        merged_df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')  # Specify semicolon delimiter

        # Serve the file as download
        with open(output_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=merged_file.csv'
            return response
    else:
        return render(request, 'tickets/prepare_import.html')
    
#ticket management
def ticket_management_dashboard(request):
    """Dashboard view for ticket management"""
    context = {
        'total_tickets': Ticket.objects.count(),
        'valid_tickets': Ticket.objects.filter(status='VALID').count(),
        'used_tickets': Ticket.objects.filter(status='USED').count(),
        'recent_tickets': Ticket.objects.all().order_by('-created_at')[:5],
        'recent_checkins': CheckIn.objects.select_related('ticket').order_by('-check_in_time')[:5],
    }
    return render(request, 'tickets/ticket_management.html', context)


def ticket_detail(request, pk):
    """Show detailed information about a specific ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    checkins = ticket.checkin_set.all().order_by('-check_in_time')
    
    context = {
        'ticket': ticket,
        'checkins': checkins,
    }
    return render(request, 'tickets/ticket_detail.html', context)

def ticket_detail_by_qr(request):
    """Show detailed information about a ticket using QR code"""
    qr_code = request.GET.get('qr_code')
    if not qr_code:
        raise Http404("No QR code provided")
    
    ticket = get_object_or_404(Ticket, qr_code=qr_code)
    checkins = ticket.checkin_set.all().order_by('-check_in_time')
    
    context = {
        'ticket': ticket,
        'checkins': checkins,
    }
    return render(request, 'tickets/ticket_detail.html', context)

def generate_sequential_qr_code():
    # Get today's date in YYYYMMDD format
    date_prefix = datetime.datetime.now().strftime("%Y%m%d")
    
    # Filter tickets created today
    today_tickets = Ticket.objects.filter(qr_code__startswith=date_prefix)
    
    if today_tickets.exists():
        # Get the highest ticket number for today and increment it
        last_ticket_number = max(
            int(ticket.qr_code[-6:]) for ticket in today_tickets
        )
        new_ticket_number = last_ticket_number + 1
    else:
        # Start from 1 if no tickets exist for today
        new_ticket_number = 1

    # Format the new ticket number as a 6-digit string with leading zeros
    ticket_number_suffix = f"{new_ticket_number:06d}"
    
    # Combine date and ticket number to form the QR code
    qr_code = f"{date_prefix}-{ticket_number_suffix}"
    return qr_code

def ticket_create(request):
    """Create a new ticket"""
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            # Assign the generated QR code
            ticket = form.save(commit=False)
            ticket.qr_code = generate_sequential_qr_code()
            ticket.save()
            messages.success(request, 'Ticket created successfully.')
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        # Generate the QR code before rendering the form
        initial_qr_code = generate_sequential_qr_code()
        form = TicketForm(initial={'status': 'VALID', 'qr_code': initial_qr_code})
        
        # Make qr_code field readonly
        form.fields['qr_code'].widget.attrs['readonly'] = 'readonly'
    
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'title': 'Create New Ticket',
        'button_text': 'Create Ticket'
    }) 

def ticket_edit(request, pk):
    """Edit an existing ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save()
            messages.success(request, 'Ticket updated successfully.')
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(instance=ticket)
    
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'ticket': ticket,
        'title': 'Edit Ticket',
        'button_text': 'Update Ticket'
    })

def ticket_delete(request, pk):
    """Delete a ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        ticket.delete()
        messages.success(request, 'Ticket deleted successfully.')
        return redirect('tickets:ticket_management')
    
    return render(request, 'tickets/ticket_confirm_delete.html', {
        'ticket': ticket
    })

@require_POST
def reset_ticket_status(request):
    """Reset selected tickets to VALID status and delete their check-ins"""
    try:
        ticket_ids = request.POST.getlist('ticket_ids')
        if not ticket_ids:
            messages.warning(request, 'No tickets were selected.')
            return redirect('tickets:ticket_management')
        
        # Get the selected tickets
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        
        # Count tickets before update
        ticket_count = tickets.count()
        
        if ticket_count > 0:
            # Delete related check-ins
            CheckIn.objects.filter(ticket__in=tickets).delete()
            
            # Reset tickets to VALID
            tickets.update(status='VALID')
            tickets.update(gdpr='NFO')
            
            messages.success(
                request, 
                f'Successfully reset {ticket_count} {"ticket" if ticket_count == 1 else "tickets"} to VALID status.'
            )
        else:
            messages.warning(request, 'No valid tickets were found to reset.')
            
    except Exception as e:
        messages.error(request, f'Error resetting tickets: {str(e)}')
    
    # Redirect back to referring page if available, otherwise to management
    return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_management'))

@require_POST
def delete_tickets(request):
    """Delete multiple selected tickets and their check-ins"""
    try:
        ticket_ids = request.POST.getlist('ticket_ids')
        if not ticket_ids:
            messages.warning(request, 'No tickets were selected.')
            return redirect('tickets:ticket_management')
        
        # Get the selected tickets
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        
        # Count tickets before deletion
        ticket_count = tickets.count()
        
        if ticket_count > 0:
            # This will also delete related check-ins due to CASCADE
            tickets.delete()
            
            messages.success(
                request, 
                f'Successfully deleted {ticket_count} {"ticket" if ticket_count == 1 else "tickets"}.'
            )
        else:
            messages.warning(request, 'No valid tickets were found to delete.')
            
    except Exception as e:
        messages.error(request, f'Error deleting tickets: {str(e)}')
    
    # Redirect back to referring page if available, otherwise to management
    return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_management'))

import csv
from django.http import HttpResponse
from .models import Ticket

def export_tickets_csv(request):
    # Create the HttpResponse object with CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'

    # Define the CSV writer and write the header row.
    writer = csv.writer(response)
    writer.writerow(['Ticket Number', 'Event Name', 'Name','Email', 'Company', 'Status', 'Last Check-In Time'])

    # Fetch all tickets and write each one to the CSV.
    tickets = Ticket.objects.all()
    for ticket in tickets:
        # Get the last check-in time, if available
        last_checkin = ticket.checkin_set.last()
        check_in_time = last_checkin.check_in_time.strftime("%Y-%m-%d %H:%M") if last_checkin else "-"
        
        writer.writerow([
            ticket.qr_code,
            ticket.event_name,
            ticket.name,
            ticket.email,
            ticket.company_name,
            ticket.status,
            check_in_time
        ])

    return response

# Config
# Config
PWIDTH	= 40		# tag width, measured in mm
PHEIGHT = 80		# tag height
PGAP 	= 2			# gap between tags
DPI		= 200		# DPI of printer
SPEED	= 3			# printing speed
DENSITY = 15		# ink density
SENSOR	= 0			# type of sensor 0>gap 1>black mark
OFFSET  = 0			# GAP offset
DOT 	= DPI//100*4# Dots per mm
CONTRAST= 128		# A number between 0~255

printerName = "TDP-225"
printerDefault = "1"

if platform.system() == "Windows":
    tsclibrary = ctypes.WinDLL("tickets/libs/TSCLIB.dll")


def get_text_size(text, font):
    lines = text.split('\n')
    widths = [font.getlength(line) for line in lines]
    heights = [font.getmetrics()[0] + font.getmetrics()[1] for line in lines]
    return max(widths), sum(heights)

def create_label_image(name, company_name=None,QR=None,printer_queue="1"):
    # Získání absolutní cesty ke složce, kde je uložen views.py
    base_dir = os.path.dirname(__file__)

    # Cesty k fontům
    font_name_path = os.path.join(base_dir, 'fonts', 'MontserratBold700.ttf')
    font_company_path = os.path.join(base_dir, 'fonts', 'MontserratSemiBold600.ttf')

    img = Image.new('L', (946, 572), color='white')
    d = ImageDraw.Draw(img)
    font_size = 250
    # Načtení fontů
    font_name = ImageFont.truetype(font_name_path, font_size)
    font_company = ImageFont.truetype(font_company_path, int(font_size * 0.70))
    wrapped_name = textwrap.wrap(name, width=18)
    wrapped_company_name = textwrap.wrap(company_name, width=20) if company_name else []
    name_width, name_height = get_text_size('\n'.join(wrapped_name), font_name)
    company_width, company_height = get_text_size('\n'.join(wrapped_company_name), font_company) if company_name else (0, 0)
    margin = 30
    while name_width > img.width - 2 * margin or company_width > img.width - 2 * margin or name_height + company_height > img.height - 2 * margin:
        font_size -= 1
        font_name = ImageFont.truetype(font_name_path, font_size)
        font_company = ImageFont.truetype(font_company_path, int(font_size * 0.70))
        name_width, name_height = get_text_size('\n'.join(wrapped_name), font_name)
        company_width, company_height = get_text_size('\n'.join(wrapped_company_name), font_company) if company_name else (0, 0)
    if company_name:
        name_y = (img.height - name_height - company_height) / 2
    else:
        name_y = (img.height - name_height) / 2
    for line in wrapped_name:
        line_width = font_name.getlength(line)
        x = max((img.width - line_width) / 2, margin)
        d.text((x, name_y), line, fill="black", font=font_name)
        name_y += font_name.getmetrics()[0] + font_name.getmetrics()[1]
    if company_name:
        company_y = name_y
        for line in wrapped_company_name:
            line_width = font_company.getlength(line)
            x = max((img.width - line_width) / 2, margin)
            d.text((x, company_y), line, fill="black", font=font_company)
            company_y += font_company.getmetrics()[0] + font_company.getmetrics()[1]
    img = img.rotate(90, expand=True)
    img.save(f"tickets/image/{name}-{QR}.png")
    printWin_TSC(f"tickets/image/{name}-{QR}.png",printer_queue)


def printWin_TSC(name,queueName):
  actualPrinter=printerName+queueName
  printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
  if actualPrinter in printers:
      print(f"tiskarna {actualPrinter} existuje")
      tsclibrary.openportW(actualPrinter);
      tsclibrary.sendcommandW("DENSITY "+str(DENSITY));
      tsclibrary.sendcommandW("SIZE " + str(PWIDTH) +" mm, " + str(PHEIGHT) +" mm");
      tsclibrary.clearbuffer();
      tsclibrary.sendcommandW("CLS");
      left = l = 0
      right = r = 253
      printOnTop(name,left)
      print("image: " + name +" send to printer")
      tsclibrary.printlabelW("1","1");
      tsclibrary.closeport();
      print('funkce printWINd done')
  else:
      print(f"tiskarna {actualPrinter} neexistuje")


def printPic(imName,x,y,mode):
	print("PRINTING ", imName)
	im = Image.open(imName)
	# im.thumbnail((PWIDTH*DOT//2,PHEIGHT*DOT))
	im.thumbnail((PWIDTH*DOT,PHEIGHT*DOT),Image.LANCZOS)
	width,height = im.size

	if width<248:	# report err for now, edit later
		print("FAILURE: IMAGE IS TOO SMALL\n")
		return -1

	im = im.convert("L") 
	data = im.getdata()
	data = np.matrix(data)
	data = data.tolist()[0]

	im1 = [1 for i in range(width*height)]
	for i in range(width*height):
		if data[i] < CONTRAST:
			im1[i] = 0
	bitmap = [0   for i in range(width*height//8)]	# sending 0 may cause some err
	offset = [255 for i in range(width*height//8)]	# so use offset to make it work
	for i in range(width*height//8):
		bitmap[i] = eval("0b"+str(im1[i*8:(i+1)*8]).replace(" ","").replace(",",'').replace("[",'').replace("]",''))
		if bitmap[i] == 0:
			bitmap[i] = 1
			offset[i] = 254
	# seeBitmap(bitmap)
	ini = "BITMAP "+str(x)+","+str(y)+","+str(width//8)+","+str(height)+","+str(mode)+","
	ini = ini.encode()
	bm = bytes(bitmap)
	ofs = bytes(offset)
	end = "\0".encode()
	tsclibrary.sendcommand(ini + bm + end);
	tsclibrary.sendcommand(ini + ofs + end);
	return 

def printOnTop(imName,position):
	printPic(imName,position,65,1)

def scanner_page1(request):
    return render(request, 'tickets/scanner.html', {'printer_queue': '1'})

def scanner_page2(request):
    return render(request, 'tickets/scanner.html', {'printer_queue': '2'})