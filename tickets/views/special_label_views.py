import time
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from ..forms import SpecialLabelForm
from ..services.printing_service import PrintingService
from ..decorators import login_required_ajax
from ..utils.error_handlers import handle_view_errors, handle_ajax_errors
from ..models import Log
from ..utils.auth_utils import get_username_for_log


@login_required_ajax
def special_labels(request):
    """Display special label printing page."""
    form = SpecialLabelForm()
    return render(request, 'tickets/special_labels.html', {'form': form})


@login_required_ajax
@require_http_methods(['POST'])
@handle_ajax_errors
def print_special_labels(request):
    """Print special labels with given details."""
    form = SpecialLabelForm(request.POST)
    
    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
    
    name = form.cleaned_data['name']
    company_name = form.cleaned_data.get('company_name', '')
    quantity = form.cleaned_data['quantity']
    printer_name = form.cleaned_data['printer']
    
    # Initialize printing service
    printing_service = PrintingService()
    
    # Override the printer name
    original_printer = printing_service.printer_name
    printing_service.printer_name = printer_name
    
    success_count = 0
    failed_count = 0
    
    try:
        for i in range(quantity):
            # Prepare label data
            label_data = {
                'name': name,
                'company_name': company_name,
                'event_name': '',  # No event name for special labels
                'qr_code': f'SPECIAL_{name}_{i+1}'  # Dummy QR for special labels
            }
            
            # Print the label
            if printing_service.print_ticket(label_data):
                success_count += 1
            else:
                failed_count += 1
            
            # Wait between prints (except for the last one)
            if i < quantity - 1:
                time.sleep(0.5)
        
        # Log the printing
        Log.objects.create(
            event_type='SYSTEM',
            message=f'Special labels printed: "{name}" x{quantity} on {printer_name} by {get_username_for_log(request)}'
        )
        
        # Restore original printer
        printing_service.printer_name = original_printer
        
        if success_count > 0:
            return JsonResponse({
                'success': True,
                'message': _('Successfully printed %(success)s labels') % {'success': success_count},
                'success_count': success_count,
                'failed_count': failed_count
            })
        else:
            return JsonResponse({
                'success': False,
                'message': _('Failed to print labels')
            }, status=500)
            
    except Exception as e:
        # Restore original printer on error
        printing_service.printer_name = original_printer
        
        Log.objects.create(
            event_type='ERROR',
            message=f'Failed to print special labels by {get_username_for_log(request)}: {str(e)}'
        )
        
        return JsonResponse({
            'success': False,
            'message': _('Error printing labels: %(error)s') % {'error': str(e)}
        }, status=500)