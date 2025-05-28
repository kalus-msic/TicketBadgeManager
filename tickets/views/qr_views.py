"""QR code generation views."""
import io
import qrcode
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ..models import Ticket
from ..decorators import login_required_ajax


@login_required_ajax
def generate_qr_code(request, ticket_id):
    """Generate QR code for a ticket."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(ticket.qr_code)
    qr.make(fit=True)
    
    # Create an image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to a BytesIO object
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Return the image
    return HttpResponse(buffer.getvalue(), content_type='image/png')