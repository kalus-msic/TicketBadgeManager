import csv
import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.db.models import Q, Prefetch
from django.core.exceptions import ValidationError
from ..models import Ticket, CheckIn, Log
from ..utils.validators import validate_qr_code, validate_email
from ..utils.text_utils import normalize_text, extract_qr_from_url

logger = logging.getLogger(__name__)


class TicketService:
    """Service for handling ticket-related business logic."""
    
    @staticmethod
    def search_tickets(search_query: str = '', status_filter: str = '') -> List[Ticket]:
        """Search tickets with optimized queries."""
        tickets = Ticket.objects.select_related().prefetch_related(
            Prefetch('checkin_set', queryset=CheckIn.objects.order_by('-check_in_time'))
        )
        
        if search_query:
            # For diacritics-insensitive search, we need to search all tickets
            # and filter in Python
            all_tickets = list(tickets)
            normalized_query = normalize_text(search_query)
            
            filtered_tickets = []
            for ticket in all_tickets:
                # Normalize ticket fields for comparison
                normalized_name = normalize_text(ticket.name or '')
                normalized_company = normalize_text(ticket.company_name or '')
                normalized_email = normalize_text(ticket.email or '')
                
                # Check if normalized query matches any normalized field
                if (normalized_query in normalized_name or
                    normalized_query in normalized_company or
                    normalized_query in normalized_email or
                    search_query.lower() in (ticket.qr_code or '').lower()):
                    filtered_tickets.append(ticket)
            
            # Convert back to queryset-like list
            ticket_ids = [t.id for t in filtered_tickets]
            tickets = tickets.filter(id__in=ticket_ids)
        
        if status_filter and status_filter != 'ALL':
            tickets = tickets.filter(status=status_filter)
        
        return tickets.order_by('-created_at')
    
    @staticmethod
    def get_ticket_by_qr(qr_code: str) -> Optional[Ticket]:
        """Get ticket by QR code with validation."""
        if not validate_qr_code(qr_code):
            raise ValidationError("Invalid QR code format")
        
        return Ticket.objects.select_related().prefetch_related('checkin_set').filter(
            qr_code=qr_code
        ).first()
    
    @staticmethod
    def verify_ticket(qr_code: str) -> Tuple[bool, str, Optional[Ticket]]:
        """Verify ticket and perform check-in if valid."""
        try:
            ticket = TicketService.get_ticket_by_qr(qr_code)
            
            if not ticket:
                Log.objects.create(
                    ticket_qr=qr_code,
                    event_type='ERROR',
                    message=f'Ticket not found: {qr_code}'
                )
                return False, "Ticket not found", None
            
            if ticket.status == 'USED':
                last_checkin = ticket.checkin_set.last()
                Log.objects.create(
                    ticket=ticket,
                    event_type='ERROR',
                    message='Attempted to use already used ticket'
                )
                return False, f"Already used at {last_checkin.check_in_time if last_checkin else 'unknown time'}", ticket
            
            if ticket.status == 'CANCELLED':
                Log.objects.create(
                    ticket=ticket,
                    event_type='ERROR',
                    message='Attempted to use cancelled ticket'
                )
                return False, "Ticket is cancelled", ticket
            
            # Perform check-in
            with transaction.atomic():
                ticket.status = 'USED'
                ticket.save()
                CheckIn.objects.create(ticket=ticket)
                Log.objects.create(
                    ticket=ticket,
                    event_type='CHECKIN',
                    message='Successful check-in'
                )
            
            return True, "Check-in successful", ticket
            
        except ValidationError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error verifying ticket {qr_code}: {e}")
            return False, "System error during verification", None
    
    @staticmethod
    def import_tickets_from_csv(file_content: str, replace_existing: bool = False) -> Dict[str, int]:
        """Import tickets from CSV content."""
        results = {
            'imported': 0,
            'errors': 0,
            'duplicates': 0
        }
        
        # Detect delimiter
        first_line = file_content.splitlines()[0]
        delimiter = ';' if ';' in first_line else ','
        
        reader = csv.DictReader(file_content.splitlines(), delimiter=delimiter)
        
        with transaction.atomic():
            if replace_existing:
                Ticket.objects.all().delete()
                Log.objects.create(
                    event_type='SYSTEM',
                    message='All existing tickets deleted for import'
                )
            
            existing_qr_codes = set(Ticket.objects.values_list('qr_code', flat=True))
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Extract data with multiple field name options
                    qr_code = (
                        row.get('Číslo vstupenky') or 
                        row.get('Ticket Number') or 
                        row.get('Unique Ticket URL') or 
                        ''
                    )
                    
                    if not qr_code:
                        logger.warning(f"Row {row_num}: Missing QR code")
                        results['errors'] += 1
                        continue
                    
                    qr_code = extract_qr_from_url(qr_code)
                    
                    if not replace_existing and qr_code in existing_qr_codes:
                        results['duplicates'] += 1
                        continue
                    
                    # Extract name
                    first_name = (
                        row.get('Jméno') or 
                        row.get('Jméno_x') or 
                        row.get('Ticket First Name') or 
                        ''
                    )
                    last_name = (
                        row.get('Příjmení') or 
                        row.get('Příjmení_x') or 
                        row.get('Ticket Last Name') or 
                        ''
                    )
                    
                    if not first_name or not last_name:
                        logger.warning(f"Row {row_num}: Missing name fields")
                        results['errors'] += 1
                        continue
                    
                    name = f"{first_name} {last_name}".strip()
                    
                    # Extract other fields
                    company_name = (
                        row.get('Firma') or 
                        row.get('Field1') or 
                        row.get('Ticket Company Name') or 
                        ''
                    ).strip()
                    
                    event_name = (
                        row.get('Akce_x') or 
                        row.get('Akce') or 
                        row.get('Event') or 
                        ''
                    ).strip()
                    
                    email = (
                        row.get('Email') or 
                        row.get('E-mail') or 
                        row.get('Ticket Email') or 
                        ''
                    ).strip()
                    
                    # Validate email if provided
                    if email and not validate_email(email):
                        logger.warning(f"Row {row_num}: Invalid email format: {email}")
                        email = ''
                    
                    # Create ticket
                    Ticket.objects.create(
                        qr_code=qr_code,
                        name=name,
                        company_name=company_name,
                        event_name=event_name,
                        email=email,
                        status='VALID'
                    )
                    
                    results['imported'] += 1
                    existing_qr_codes.add(qr_code)
                    
                except Exception as e:
                    logger.error(f"Row {row_num}: Import error: {e}")
                    results['errors'] += 1
        
        Log.objects.create(
            event_type='SYSTEM',
            message=f"CSV import completed: {results['imported']} imported, "
                   f"{results['errors']} errors, {results['duplicates']} duplicates"
        )
        
        return results
    
    @staticmethod
    def get_statistics() -> Dict[str, int]:
        """Get ticket statistics with optimized queries."""
        from django.db.models import Count, Q
        from django.db.models.functions import TruncHour, TruncDate
        from django.utils import timezone
        from datetime import timedelta
        
        stats = Ticket.objects.aggregate(
            total=Count('id'),
            valid=Count('id', filter=Q(status='VALID')),
            used=Count('id', filter=Q(status='USED')),
            cancelled=Count('id', filter=Q(status='CANCELLED'))
        )
        
        stats['checkins'] = CheckIn.objects.count()
        stats['percentage_checked_in'] = round(
            (stats['used'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1
        )
        
        # Check-ins by hour for last 24 hours
        last_24h = timezone.now() - timedelta(hours=24)
        stats['checkins_by_hour'] = list(
            CheckIn.objects
            .filter(check_in_time__gte=last_24h)
            .annotate(hour=TruncHour('check_in_time'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        
        # Recent check-ins rate (last hour vs previous hour)
        last_hour = timezone.now() - timedelta(hours=1)
        prev_hour = timezone.now() - timedelta(hours=2)
        
        last_hour_count = CheckIn.objects.filter(check_in_time__gte=last_hour).count()
        prev_hour_count = CheckIn.objects.filter(
            check_in_time__gte=prev_hour,
            check_in_time__lt=last_hour
        ).count()
        
        stats['last_hour_checkins'] = last_hour_count
        stats['checkin_trend'] = 'up' if last_hour_count > prev_hour_count else (
            'down' if last_hour_count < prev_hour_count else 'stable'
        )
        
        return stats