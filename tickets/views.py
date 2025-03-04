import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
import pandas as pd
import os
import datetime
import ctypes
import platform
from PIL import Image, ImageDraw, ImageFont
import textwrap
import requests
import unicodedata


# Import modelů a formulářů
from .models import Ticket, CheckIn, Log, EventeeSettings
from .forms import CsvImportForm, TicketForm

if platform.system() == "Windows":
    try:
        import win32print
    except ImportError as e:
        print("Chyba při načítání win32print:", e)
        Log.objects.create(ticket=None, event_type='ERROR', message=f"Chyba při načítání win32print: {e}")
    # Načtení TSCLIB.dll s kontrolou existence souboru
    tsclib_path = os.path.join(os.path.dirname(__file__), "libs", "TSCLIB.dll")
    if os.path.exists(tsclib_path):
        try:
            tsclibrary = ctypes.WinDLL(tsclib_path)
        except Exception as e:
            print("Chyba při načítání TSCLIB.dll:", e)
            Log.objects.create(ticket=None, event_type='ERROR', message=f"Chyba při načítání TSCLIB.dll: {e}")
            tsclibrary = None
    else:
        print(f"TSCLIB.dll nebyl nalezen na {tsclib_path}")
        Log.objects.create(ticket=None, event_type='SYSTEM', message=f"TSCLIB.dll nebyl nalezen na {tsclib_path}")
        tsclibrary = None
else:
    print("win32print is not available on this platform.")
    tsclibrary = None

def index(request):
    total_tickets = Ticket.objects.count()
    valid_tickets = Ticket.objects.filter(status='VALID').count()
    used_tickets = Ticket.objects.filter(status='USED').count()
    total_checkins = CheckIn.objects.count()
    
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
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    # Načteme všechny tickety (pro malé množství dat)
    tickets = list(Ticket.objects.all().order_by('-created_at'))

    # Filtrace podle vyhledávacího dotazu (bez diakritiky)
    if search_query:
        normalized_query = normalize_text(search_query)
        tickets = [
            ticket for ticket in tickets
            if normalized_query in normalize_text(ticket.name)
            or normalized_query in normalize_text(ticket.company_name)
            or normalized_query in normalize_text(ticket.qr_code)
        ]

    # Filtrace podle stavu
    if status_filter and status_filter != 'ALL':
        tickets = [ticket for ticket in tickets if ticket.status == status_filter]

    paginator = Paginator(tickets, 25)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)

    context = {
        'tickets': tickets_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': Ticket.objects.count(),
        'valid_count': len([t for t in Ticket.objects.all() if t.status == 'VALID']),
        'used_count': len([t for t in Ticket.objects.all() if t.status == 'USED']),
    }

    # Pokud je požadavek AJAX (pro dynamické vyhledávání), vrátíme pouze fragment s tabulkou
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'tickets/_ticket_table.html', context)
    else:
        return render(request, 'tickets/ticket_list.html', context)
    
def detect_delimiter(file_content):
    first_line = file_content.splitlines()[0]
    if ';' in first_line:
        return ';'
    return ','

def import_page(request):
    form = CsvImportForm()
    return render(request, 'tickets/import.html', {
        'form': form,
        'current_ticket_count': Ticket.objects.count()
    })

def import_replace_tickets(request):
    if request.method == 'POST':
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file_content = request.FILES['csv_file'].read().decode('utf-8-sig')
                delimiter = ';' if ';' in file_content.splitlines()[0] else ','
                
                reader = csv.DictReader(file_content.splitlines(), delimiter=delimiter)
                print(f"Found CSV columns: {reader.fieldnames}")
                print(f"Using delimiter: {delimiter}")
                
                imported_count = 0
                error_count = 0
                
                with transaction.atomic():
                    Ticket.objects.all().delete()
                    
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
                                Log.objects.create(ticket=None, event_type='SYSTEM', message=f"Skipping row, missing required fields: {row}")
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
                            Log.objects.create(ticket=None, event_type='ERROR', message=f"Error processing row {row}: {e}")
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
                Log.objects.create(ticket=None, event_type='ERROR', message=f"Import failed: {e}")
                
    return redirect('tickets:import_page')

def import_add_tickets(request):
    if request.method == 'POST':
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file_content = request.FILES['csv_file'].read().decode('utf-8-sig')
                delimiter = ';' if ';' in file_content.splitlines()[0] else ','
                
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
                                Log.objects.create(ticket=None, event_type='SYSTEM', message=f"Skipping row, missing required fields: {row}")
                                error_count += 1
                                continue
                            
                            name = f"{first_name} {last_name}".strip()
                            qr_code = qr_code.strip()
                            company_name = company_name.strip() if company_name else ''
                            
                            if qr_code in existing_qr_codes:
                                print(f"Duplicate QR code found: {qr_code}")
                                Log.objects.create(ticket=None, event_type='SYSTEM', message=f"Duplicate QR code found: {qr_code}")
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
                            existing_qr_codes.add(qr_code)
                            
                        except Exception as e:
                            print(f"Error processing row: {row}. Error: {str(e)}")
                            Log.objects.create(ticket=None, event_type='ERROR', message=f"Error processing row {row}: {e}")
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
                Log.objects.create(ticket=None, event_type='ERROR', message=f"Import failed: {e}")
                
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
                previous_status = ticket.status
                ticket.status = 'USED'
                ticket.save()
                
                Log.objects.create(ticket=ticket, event_type='CHECKIN', message='Ticket checked in')
                
                response = JsonResponse({
                    'valid': True,
                    'message': 'Valid ticket!',
                    'qr_code': ticket.qr_code,
                    'name': ticket.name,
                    'company': ticket.company_name,
                    'event_name': ticket.event_name,
                })
                
                try:
                    # Předáváme aktuální ticket jako ticket_obj pro logování případných chyb
                    create_label_image(ticket.name, ticket.company_name, ticket.qr_code, printer_queue, ticket)
                except Exception as e:
                    Log.objects.create(ticket=ticket, event_type='ERROR', message=f"Chyba při tisku štítku: {e}")
                
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

    if request.method == 'GET':
        return render(request, 'tickets/scanner.html')

    return JsonResponse({'error': 'Invalid request method'})

def settings(request):
    ticket_count = Ticket.objects.count()
    checkin_count = CheckIn.objects.count()
    logs_count = Log.objects.count()
    eventee_setting = EventeeSettings.objects.first()
    context = {
        'ticket_count': ticket_count,
        'checkin_count': checkin_count,
        'logs_count': logs_count,
        'eventee_token': eventee_setting.api_token if eventee_setting else "",
    }
    return render(request, 'tickets/settings.html', context)


def delete_all_data(request):
    if request.method == 'POST':
        try:
            tickets_count = Ticket.objects.count()
            checkins_count = CheckIn.objects.count()
            Ticket.objects.all().delete()
            messages.success(
                request, 
                f'Successfully deleted all data: {tickets_count} tickets and {checkins_count} check-ins.'
            )
        except Exception as e:
            messages.error(request, f'Error deleting data: {str(e)}')
            Log.objects.create(ticket=None, event_type='ERROR', message=f"Error deleting all data: {e}")
    return redirect('tickets:settings')

def delete_checkins(request):
    if request.method == 'POST':
        try:
            checkins_count = CheckIn.objects.count()
            CheckIn.objects.all().delete()
            Ticket.objects.all().update(status='VALID')
            messages.success(request, f'Successfully deleted {checkins_count} check-ins. All tickets reset to VALID status.')
        except Exception as e:
            messages.error(request, f'Error deleting check-ins: {str(e)}')
            Log.objects.create(ticket=None, event_type='ERROR', message=f"Error deleting check-ins: {e}")
    return redirect('tickets:settings')

def merge_import(request):
    if request.method == 'POST' and 'file1' in request.FILES and 'file2' in request.FILES:
        file1 = request.FILES['file1']
        file2 = request.FILES['file2']
        file1_path = default_storage.save('temp/' + file1.name, file1)
        file2_path = default_storage.save('temp/' + file2.name, file2)

        df1 = pd.read_excel(file1_path, engine='openpyxl')
        df2 = pd.read_excel(file2_path, engine='openpyxl')

        missing_columns = []
        if 'Číslo vstupenky' not in df1.columns:
            missing_columns.append("File 1 missing 'Číslo vstupenky': " + ", ".join(str(col) for col in df1.columns))
        if 'Číslo vstupenky' not in df2.columns:
            missing_columns.append("File 2 missing 'Číslo vstupenky': " + ", ".join(str(col) for col in df2.columns))

        if missing_columns:
            error_message = "The required column 'Číslo vstupenky' is missing in one of the files.<br>" + "<br>".join(missing_columns)
            return HttpResponse(error_message, status=400)

        df1['Číslo vstupenky'] = df1['Číslo vstupenky'].astype(str).str.strip()
        df2['Číslo vstupenky'] = df2['Číslo vstupenky'].astype(str).str.strip()

        merged_df = pd.merge(df1, df2, on='Číslo vstupenky', how='right')
        output_path = 'temp/merged_file.csv'
        merged_df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')

        with open(output_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=merged_file.csv'
            return response
    else:
        return render(request, 'tickets/prepare_import.html')
    
def ticket_management_dashboard(request):
    context = {
        'total_tickets': Ticket.objects.count(),
        'valid_tickets': Ticket.objects.filter(status='VALID').count(),
        'used_tickets': Ticket.objects.filter(status='USED').count(),
        'recent_tickets': Ticket.objects.all().order_by('-created_at')[:5],
        'recent_checkins': CheckIn.objects.select_related('ticket').order_by('-check_in_time')[:5],
    }
    return render(request, 'tickets/ticket_management.html', context)

def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    checkins = ticket.checkin_set.all().order_by('-check_in_time')
    
    context = {
        'ticket': ticket,
        'checkins': checkins,
    }
    return render(request, 'tickets/ticket_detail.html', context)

def ticket_detail_by_qr(request):
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
    date_prefix = datetime.datetime.now().strftime("%Y%m%d")
    today_tickets = Ticket.objects.filter(qr_code__startswith=date_prefix)
    
    if today_tickets.exists():
        last_ticket_number = max(
            int(ticket.qr_code[-6:]) for ticket in today_tickets
        )
        new_ticket_number = last_ticket_number + 1
    else:
        new_ticket_number = 1

    ticket_number_suffix = f"{new_ticket_number:06d}"
    qr_code = f"{date_prefix}-{ticket_number_suffix}"
    return qr_code


def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.qr_code = generate_sequential_qr_code()
            ticket.save()
            Log.objects.create(ticket=ticket, event_type='OTHER', message='Ticket created')
            
            # Pokud byl checkbox "Invite to Eventee" zaškrtnutý a ticket ještě nebyl pozván
            if request.POST.get("invite_to_eventee") and not ticket.invited:
                # Rozdělení jména na křestní a příjmení
                name_parts = ticket.name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Upravený payload s klíčem "users"
                payload = {
                    "users": [
                        {
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": ticket.email,
                        }
                    ]
                }
                
                try:
                    # Načtení API tokenu z EventeeSettings
                    eventee_setting = EventeeSettings.objects.first()
                    token = eventee_setting.api_token if eventee_setting and eventee_setting.api_token else ""
                    
                    headers = {
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}"
                    }
                    
                    api_url = "https://api.eventee.co/public/v1/attendee/invite"
                    response = requests.put(api_url, json=payload, headers=headers)
                    
                    if response.ok:
                        Log.objects.create(
                            ticket=ticket,
                            event_type='OTHER',
                            message=f"Eventee invitation sent successfully: {response.text}"
                        )
                        ticket.invited = True
                        ticket.save()
                    else:
                        Log.objects.create(
                            ticket=ticket,
                            event_type='ERROR',
                            message=f"Failed to send Eventee invitation: {response.status_code}, {response.text}"
                        )
                except Exception as e:
                    Log.objects.create(
                        ticket=ticket,
                        event_type='ERROR',
                        message=f"Error calling Eventee API: {e}"
                    )
            
            messages.success(request, 'Ticket created successfully.')
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        initial_qr_code = generate_sequential_qr_code()
        form = TicketForm(initial={'status': 'VALID', 'qr_code': initial_qr_code})
        form.fields['qr_code'].widget.attrs['readonly'] = 'readonly'
    
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'title': 'Create New Ticket',
        'button_text': 'Create Ticket'
    })

def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    old_name = ticket.name
    old_company_name = ticket.company_name
    old_email = ticket.email
    old_status = ticket.status

    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            changes = []
            if old_name != ticket.name:
                changes.append(f"Name changed from '{old_name}' to '{ticket.name}'")
            if old_company_name != ticket.company_name:
                changes.append(f"Company changed from '{old_company_name}' to '{ticket.company_name}'")
            if old_email != ticket.email:
                changes.append(f"Email changed from '{old_email}' to '{ticket.email}'")
            if old_status != ticket.status:
                changes.append(f"Status changed from '{old_status}' to '{ticket.status}'")
            
            # Pokud checkbox "Invite to Eventee" je zaškrtnutý a ticket ještě nebyl pozván
            if form.cleaned_data.get("invite_to_eventee") and not ticket.invited:
                name_parts = ticket.name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Upravený payload s klíčem "users"
                payload = {
                    "users": [
                        {
                            "firstName": first_name,
                            "lastName": last_name,
                            "email": ticket.email,
                        }
                    ]
                }
                
                try:
                    eventee_setting = EventeeSettings.objects.first()
                    token = eventee_setting.api_token if eventee_setting and eventee_setting.api_token else ""
                    
                    headers = {
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}"
                    }
                    
                    api_url = "https://api.eventee.co/public/v1/attendee/invite"
                    response = requests.put(api_url, json=payload, headers=headers)
                    
                    if response.ok:
                        Log.objects.create(
                            ticket=ticket,
                            event_type='OTHER',
                            message=f"Eventee invitation sent successfully on update: {response.text}"
                        )
                        ticket.invited = True
                        changes.append("Invitation sent")
                    else:
                        Log.objects.create(
                            ticket=ticket,
                            event_type='ERROR',
                            message=f"Failed to send Eventee invitation on update: {response.status_code}, {response.text}"
                        )
                except Exception as e:
                    Log.objects.create(
                        ticket=ticket,
                        event_type='ERROR',
                        message=f"Error calling Eventee API on update: {e}"
                    )
            
            ticket.save()
            if changes:
                Log.objects.create(ticket=ticket, event_type='UPDATE', message="; ".join(changes))
                
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
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        log_message = f"Ticket {ticket.qr_code} ({ticket.name}) deleted."
        Log.objects.create(
            ticket=ticket,
            ticket_qr=ticket.qr_code,
            event_type='OTHER',
            message=log_message
        )
        ticket.delete()
        messages.success(request, 'Ticket deleted successfully.')
        return redirect('tickets:ticket_management')
    
    return render(request, 'tickets/ticket_confirm_delete.html', {
        'ticket': ticket
    })

@require_POST
def reset_ticket_status(request):
    try:
        ticket_ids = request.POST.getlist('ticket_ids')
        if not ticket_ids:
            messages.warning(request, 'No tickets were selected.')
            return redirect('tickets:ticket_management')
        
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        ticket_count = tickets.count()
        
        if ticket_count > 0:
            CheckIn.objects.filter(ticket__in=tickets).delete()
            
            for ticket in tickets:
                previous_status = ticket.status
                ticket.status = 'VALID'
                ticket.gdpr = 'NFO'
                ticket.save()
                Log.objects.create(ticket=ticket, event_type='UPDATE', message=f"Status reset from {previous_status} to VALID. Check-ins deleted.")
            
            messages.success(
                request, 
                f'Successfully reset {ticket_count} {"ticket" if ticket_count == 1 else "tickets"} to VALID status.'
            )
        else:
            messages.warning(request, 'No valid tickets were found to reset.')
            
    except Exception as e:
        messages.error(request, f'Error resetting tickets: {str(e)}')
        Log.objects.create(ticket=None, event_type='ERROR', message=f"Error resetting tickets: {e}")
    
    return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_management'))

@require_POST
def delete_tickets(request):
    try:
        ticket_ids = request.POST.getlist('ticket_ids')
        if not ticket_ids:
            messages.warning(request, 'No tickets were selected.')
            return redirect('tickets:ticket_management')
        
        tickets = Ticket.objects.filter(id__in=ticket_ids)
        ticket_count = tickets.count()
        
        if ticket_count > 0:
            for ticket in tickets:
                Log.objects.create(ticket=ticket, event_type='OTHER', message='Ticket deleted via bulk action')
            tickets.delete()
            messages.success(
                request, 
                f'Successfully deleted {ticket_count} {"ticket" if ticket_count == 1 else "tickets"}.'
            )
        else:
            messages.warning(request, 'No valid tickets were found to delete.')
            
    except Exception as e:
        messages.error(request, f'Error deleting tickets: {str(e)}')
        Log.objects.create(ticket=None, event_type='ERROR', message=f"Error deleting tickets: {e}")
    
    return redirect(request.META.get('HTTP_REFERER', 'tickets:ticket_management'))

def export_tickets_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ticket Number', 'Event Name', 'Name', 'Email', 'Company', 'Status', 'Last Check-In Time'])

    tickets = Ticket.objects.all()
    for ticket in tickets:
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

# Label printing configuration a funkce
PWIDTH    = 40
PHEIGHT   = 80
DPI       = 200
DENSITY   = 15
DOT       = DPI // 100 * 4
CONTRAST  = 128

printerName = "TDP-225"

def get_text_size(text, font):
    lines = text.split('\n')
    widths = [font.getlength(line) for line in lines]
    heights = [font.getmetrics()[0] + font.getmetrics()[1] for line in lines]
    return max(widths), sum(heights)

def create_label_image(name, company_name=None, QR=None, printer_queue="1", ticket_obj=None):
    base_dir = os.path.dirname(__file__)
    font_name_path = os.path.join(base_dir, 'fonts', 'MontserratBold700.ttf')
    font_company_path = os.path.join(base_dir, 'fonts', 'MontserratSemiBold600.ttf')

    # Ověříme existenci fontů
    if not os.path.exists(font_name_path) or (company_name and not os.path.exists(font_company_path)):
        err_msg = f"Chybí fonty. Očekávány cesty: {font_name_path} a {font_company_path}"
        print(err_msg)
        Log.objects.create(ticket=ticket_obj, event_type='ERROR', message=err_msg)
        return

    font_size = 250
    try:
        font_name = ImageFont.truetype(font_name_path, font_size)
        font_company = ImageFont.truetype(font_company_path, int(font_size * 0.70))
    except Exception as e:
        err_msg = f"Chyba při načítání fontů: {e}"
        print(err_msg)
        Log.objects.create(ticket=ticket_obj, event_type='ERROR', message=err_msg)
        return

    img = Image.new('L', (946, 572), color='white')
    d = ImageDraw.Draw(img)
    wrapped_name = textwrap.wrap(name, width=18)
    wrapped_company_name = textwrap.wrap(company_name, width=20) if company_name else []
    name_width, name_height = get_text_size('\n'.join(wrapped_name), font_name)
    company_width, company_height = get_text_size('\n'.join(wrapped_company_name), font_company) if company_name else (0, 0)
    margin = 30
    while name_width > img.width - 2 * margin or company_width > img.width - 2 * margin or name_height + company_height > img.height - 2 * margin:
        font_size -= 1
        try:
            font_name = ImageFont.truetype(font_name_path, font_size)
            font_company = ImageFont.truetype(font_company_path, int(font_size * 0.70))
        except Exception as e:
            err_msg = f"Chyba při úpravě velikosti fontu: {e}"
            print(err_msg)
            Log.objects.create(ticket=ticket_obj, event_type='ERROR', message=err_msg)
            return
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
    try:
        output_dir = os.path.join(base_dir, "image")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        image_file = os.path.join(output_dir, f"{name}-{QR}.png")
        img.save(image_file)
        # Předáváme také ticket_obj dál pro logování chyb v tiskové funkci
        printWin_TSC(image_file, printer_queue, ticket_obj)
    except Exception as e:
        err_msg = f"Chyba při ukládání obrázku nebo odesílání na tiskárnu: {e}"
        print(err_msg)
        Log.objects.create(ticket=ticket_obj, event_type='ERROR', message=err_msg)
        return

def printWin_TSC(name, queueName, ticket_obj=None):
    if platform.system() != "Windows":
        err_msg = "Tisk pomocí TSC tiskárny není podporován mimo Windows."
        print(err_msg)
        Log.objects.create(ticket=ticket_obj, event_type='SYSTEM', message=err_msg)
        return
    if tsclibrary is None:
        err_msg = "TSC knihovna není dostupná."
        print(err_msg)
        Log.objects.create(ticket=ticket_obj, event_type='ERROR', message=err_msg)
        return
    try:
        actualPrinter = printerName + queueName
        printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
        if actualPrinter in printers:
            print(f"Printer {actualPrinter} exists")
            tsclibrary.openportW(actualPrinter)
            tsclibrary.sendcommandW("DENSITY " + str(DENSITY))
            tsclibrary.sendcommandW("SIZE " + str(PWIDTH) + " mm, " + str(PHEIGHT) + " mm")
            tsclibrary.clearbuffer()
            tsclibrary.sendcommandW("CLS")
            left = 0
            printOnTop(name, left)
            print("Image " + name + " sent to printer")
            tsclibrary.printlabelW("1", "1")
            tsclibrary.closeport()
            print('printWin_TSC function completed')
        else:
            err_msg = f"Printer {actualPrinter} does not exist"
            print(err_msg)
            Log.objects.create(ticket=ticket_obj, event_type='SYSTEM', message=err_msg)
    except Exception as e:
        err_msg = f"Chyba při komunikaci s tiskárnou: {e}"
        print(err_msg)
        Log.objects.create(ticket=ticket_obj, event_type='ERROR', message=err_msg)

def printPic(imName, x, y, mode):
    print("PRINTING ", imName)
    im = Image.open(imName)
    im.thumbnail((PWIDTH * DOT, PHEIGHT * DOT), Image.LANCZOS)
    width, height = im.size

    if width < 248:
        print("FAILURE: IMAGE IS TOO SMALL\n")
        return -1

    im = im.convert("L")
    data = list(im.getdata())
    im1 = [1 if d >= CONTRAST else 0 for d in data]
    bitmap = [0 for _ in range(width * height // 8)]
    offset = [255 for _ in range(width * height // 8)]
    for i in range(width * height // 8):
        bits = im1[i*8:(i+1)*8]
        binary_str = "0b" + "".join(str(bit) for bit in bits)
        bitmap[i] = eval(binary_str)
        if bitmap[i] == 0:
            bitmap[i] = 1
            offset[i] = 254
    ini = "BITMAP " + str(x) + "," + str(y) + "," + str(width // 8) + "," + str(height) + "," + str(mode) + ","
    ini = ini.encode()
    bm = bytes(bitmap)
    ofs = bytes(offset)
    end = "\0".encode()
    tsclibrary.sendcommand(ini + bm + end)
    tsclibrary.sendcommand(ini + ofs + end)
    return 

def printOnTop(imName, position):
    printPic(imName, position, 65, 1)

def scanner_page1(request):
    return render(request, 'tickets/scanner.html', {'printer_queue': '1'})

def scanner_page2(request):
    return render(request, 'tickets/scanner.html', {'printer_queue': '2'})

from django.core.paginator import Paginator

def ticket_log_list(request):
    """
    View to list Logs entries with filtering options:
    - ticket: filtruje podle ID nebo částečného shody s QR kódem
    - event_type: filtruje podle typu události (např. CHECKIN, UPDATE, OTHER, ERROR, SYSTEM)
    - search: vyhledávání ve zprávě
    """
    logs = Log.objects.select_related('ticket').all().order_by('-timestamp')
    
    # Filtrace podle vstupenky (ID nebo částečná shoda s QR kódem)
    ticket_filter = request.GET.get('ticket')
    if ticket_filter:
        logs = logs.filter(Q(ticket__id=ticket_filter) | Q(ticket__qr_code__icontains=ticket_filter))
    
    # Filtrace podle event typu
    event_type = request.GET.get('event_type')
    if event_type:
        logs = logs.filter(event_type=event_type)
    
    # Vyhledávání ve zprávě
    search = request.GET.get('search')
    if search:
        logs = logs.filter(message__icontains=search)
    
    # Stránkování – zobrazíme 25 záznamů na stránku
    paginator = Paginator(logs, 25)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
        'ticket_filter': ticket_filter or '',
        'event_type': event_type or '',
        'search': search or '',
        'event_choices': Log.EVENT_CHOICES,
    }
    return render(request, 'tickets/log.html', context)

@require_POST
def delete_logs(request):
    try:
        logs_count = Log.objects.count()
        Log.objects.all().delete()
        messages.success(request, f"Successfully deleted {logs_count} log entries.")
    except Exception as e:
        messages.error(request, f"Error deleting logs: {e}")
    return redirect('tickets:settings')

def update_eventee_token(request):
    token = request.POST.get('api_token', '').strip()
    setting, created = EventeeSettings.objects.get_or_create(id=1)
    setting.api_token = token
    setting.save()
    messages.success(request, "Eventee API token updated.")
    return redirect('tickets:settings')

def normalize_text(text):
    """Odstraní diakritiku a převede text na malá písmena."""
    if not text:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()
