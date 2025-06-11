"""QR code generation views."""
import io
import qrcode
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ..models import Ticket
from ..decorators import login_required_ajax
from ..utils.validators import sanitize_string


@login_required_ajax
def generate_qr_code(request, ticket_id=None):
    """Generate QR code for a ticket or any URL."""
    # Check if we should generate QR for URL (from GET parameter)
    url_param = request.GET.get('url', '')
    
    if url_param:
        # Generate QR for URL
        data = url_param
    elif ticket_id:
        # Generate QR for ticket
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        data = ticket.qr_code
    else:
        # No data provided
        return HttpResponse(status=400)
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create an image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to a BytesIO object
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Return the image
    return HttpResponse(buffer.getvalue(), content_type='image/png')