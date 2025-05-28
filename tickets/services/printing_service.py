import os
import platform
import ctypes
import logging
from PIL import Image, ImageDraw, ImageFont
import textwrap
from typing import Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


class PrintingService:
    """Service for handling ticket/badge printing operations."""
    
    LABEL_WIDTH = 464
    LABEL_HEIGHT = 271
    QR_SIZE = 150
    MARGIN = 10
    
    def __init__(self):
        self.tsclibrary = None
        self.printer_name = None
        self._initialize_printer()
    
    def _initialize_printer(self):
        """Initialize printer based on platform."""
        if platform.system() == "Windows":
            try:
                import win32print
                self.printer_name = win32print.GetDefaultPrinter()
                logger.info(f"Default printer set to: {self.printer_name}")
                
                # Load TSCLIB.dll
                tsclib_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    "libs", 
                    "TSCLIB.dll"
                )
                if os.path.exists(tsclib_path):
                    try:
                        self.tsclibrary = ctypes.WinDLL(tsclib_path)
                        logger.info("TSCLIB.dll loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load TSCLIB.dll: {e}")
                else:
                    logger.warning(f"TSCLIB.dll not found at {tsclib_path}")
            except ImportError:
                logger.error("win32print module not available")
            except Exception as e:
                logger.error(f"Failed to initialize printer: {e}")
        else:
            logger.info(f"Running on {platform.system()} - TSC printer support not available")
    
    def print_ticket(self, ticket_data: dict) -> bool:
        """Print a ticket with the given data."""
        if platform.system() != "Windows":
            os_name = platform.system()
            logger.warning(f"Label printing not supported on {os_name}. TSC printer library (TSCLIB.dll) requires Windows.")
            # Log to database for user visibility
            from ..models import Log
            Log.objects.create(
                event_type='ERROR',
                message=f'Label printing attempted on {os_name} - not supported. TSC printers require Windows with TSCLIB.dll'
            )
            return False
            
        if not self.tsclibrary or not self.printer_name:
            logger.error("Printer not properly initialized - TSCLIB.dll not loaded or no printer configured")
            return False
        
        try:
            # Generate ticket image
            image_path = self._generate_ticket_image(ticket_data)
            
            # Print the image
            success = self._send_to_printer(image_path)
            
            # Clean up
            if os.path.exists(image_path):
                os.remove(image_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to print ticket: {e}")
            return False
    
    def _generate_ticket_image(self, ticket_data: dict) -> str:
        """Generate ticket image with QR code and text."""
        import qrcode
        from django.conf import settings
        
        # Create blank image
        img = Image.new('RGB', (self.LABEL_WIDTH, self.LABEL_HEIGHT), 'white')
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        font_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "fonts"
        )
        try:
            font_bold = ImageFont.truetype(
                os.path.join(font_path, "MontserratBold700.ttf"), 16
            )
            font_regular = ImageFont.truetype(
                os.path.join(font_path, "MontserratSemiBold600.ttf"), 14
            )
            # Larger font for special labels
            font_extra_large = ImageFont.truetype(
                os.path.join(font_path, "MontserratBold700.ttf"), 24
            )
        except:
            font_bold = ImageFont.load_default()
            font_regular = ImageFont.load_default()
            font_extra_large = font_bold
        
        # Check if this is a special label (no real QR code)
        is_special_label = ticket_data.get('qr_code', '').startswith('SPECIAL_')
        
        if not is_special_label:
            # Generate QR code for regular tickets
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr.add_data(ticket_data.get('qr_code', ''))
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((self.QR_SIZE, self.QR_SIZE))
            
            # Paste QR code
            img.paste(qr_img, (self.MARGIN, self.MARGIN))
            
            # Add text next to QR code
            text_x = self.QR_SIZE + self.MARGIN * 2
            text_y = self.MARGIN
        else:
            # For special labels, center the text without QR code
            text_x = self.MARGIN
            text_y = self.LABEL_HEIGHT // 3
        
        # Name
        name = ticket_data.get('name', '')
        
        if is_special_label:
            # For special labels, use larger font and center the name
            # Calculate text width to center it
            bbox = draw.textbbox((0, 0), name, font=font_extra_large)
            text_width = bbox[2] - bbox[0]
            text_x = (self.LABEL_WIDTH - text_width) // 2
            draw.text((text_x, text_y), name, font=font_extra_large, fill='black')
            text_y += 50
        else:
            # Regular ticket layout
            wrapped_name = textwrap.fill(name, width=20)
            draw.text((text_x, text_y), wrapped_name, font=font_bold, fill='black')
            text_y += 40
        
        # Company
        company = ticket_data.get('company_name', '')
        if company:
            if is_special_label:
                # Center company name for special labels
                bbox = draw.textbbox((0, 0), company, font=font_regular)
                text_width = bbox[2] - bbox[0]
                text_x = (self.LABEL_WIDTH - text_width) // 2
                draw.text((text_x, text_y), company, font=font_regular, fill='black')
            else:
                wrapped_company = textwrap.fill(company, width=25)
                draw.text((text_x, text_y), wrapped_company, font=font_regular, fill='black')
        
        # Event name (only for regular tickets)
        if not is_special_label and ticket_data.get('event_name'):
            text_y += 40
            draw.text((text_x, text_y), ticket_data['event_name'], font=font_regular, fill='black')
        
        # Save image
        temp_filename = f"label_{ticket_data['qr_code'].replace('/', '_')}.png"
        temp_path = os.path.join(settings.BASE_DIR, 'temp', temp_filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        img.save(temp_path)
        
        return temp_path
    
    def _send_to_printer(self, image_path: str) -> bool:
        """Send image to printer using TSCLIB."""
        try:
            # TSCLIB commands
            self.tsclibrary.openport.argtypes = [ctypes.c_char_p]
            self.tsclibrary.openport(self.printer_name.encode('utf-8'))
            
            self.tsclibrary.sendcommand(b"SIZE 58 mm, 34 mm")
            self.tsclibrary.sendcommand(b"SPEED 4")
            self.tsclibrary.sendcommand(b"DENSITY 10")
            self.tsclibrary.sendcommand(b"DIRECTION 1")
            self.tsclibrary.sendcommand(b"REFERENCE 0,0")
            self.tsclibrary.sendcommand(b"CLS")
            
            # Send image
            self.tsclibrary.downloadpcx.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.tsclibrary.downloadpcx(image_path.encode('utf-8'), b"TICKET.PCX")
            self.tsclibrary.sendcommand(b"PUTPCX 0,0,\"TICKET.PCX\"")
            
            # Print
            self.tsclibrary.printlabel(b"1", b"1")
            self.tsclibrary.closeport()
            
            logger.info(f"Successfully printed ticket from {image_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send to printer: {e}")
            return False