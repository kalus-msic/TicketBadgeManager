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
    
    # Label size 40x80mm at 203 DPI (8 dots/mm)
    # 40mm = 320 pixels, 80mm = 640 pixels
    LABEL_WIDTH = 320  # 40mm
    LABEL_HEIGHT = 640  # 80mm
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
            error_msg = "Printer not properly initialized - TSCLIB.dll not loaded or no printer configured"
            logger.error(error_msg)
            # Log to database for user visibility
            from ..models import Log
            Log.objects.create(
                event_type='ERROR',
                message=f'Print failed: {error_msg}'
            )
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
            error_msg = f"Failed to print ticket: {e}"
            logger.error(error_msg)
            # Log to database for user visibility
            from ..models import Log
            Log.objects.create(
                event_type='ERROR',
                message=f'Print failed: {error_msg}'
            )
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
        
        # Get text to display
        name = ticket_data.get('name', '')
        company = ticket_data.get('company_name', '')
        is_special_label = ticket_data.get('qr_code', '').startswith('SPECIAL_')
        
        # Calculate available space - always use full width (no QR code)
        available_width = self.LABEL_WIDTH - (self.MARGIN * 2)
        text_start_y = self.LABEL_HEIGHT // 3  # Start text in upper third of label
        
        # Find optimal font size
        name_font_size = 30  # Start with larger size
        min_font_size = 12   # Minimum readable size
        
        while name_font_size >= min_font_size:
            try:
                font_bold = ImageFont.truetype(
                    os.path.join(font_path, "MontserratBold700.ttf"), 
                    name_font_size
                )
                font_regular = ImageFont.truetype(
                    os.path.join(font_path, "MontserratSemiBold600.ttf"), 
                    int(name_font_size * 0.7)  # Company font is 70% of name size
                )
            except:
                font_bold = ImageFont.load_default()
                font_regular = ImageFont.load_default()
            
            # Test if text fits
            name_lines = self._wrap_text(name, font_bold, available_width)
            company_lines = self._wrap_text(company, font_regular, available_width) if company else []
            
            # Calculate total height needed
            line_height = int(name_font_size * 1.2)
            company_line_height = int(name_font_size * 0.7 * 1.2)
            total_height = (len(name_lines) * line_height + 
                           len(company_lines) * company_line_height)
            
            # Check if it fits vertically
            max_height = self.LABEL_HEIGHT - text_start_y - self.MARGIN
            
            if total_height <= max_height:
                break  # Found good size
            
            name_font_size -= 2  # Reduce and try again
        
        # Draw the text - always centered
        y_pos = text_start_y
        
        # Draw name
        for line in name_lines:
            bbox = draw.textbbox((0, 0), line, font=font_bold)
            text_width = bbox[2] - bbox[0]
            x_pos = (self.LABEL_WIDTH - text_width) // 2
            draw.text((x_pos, y_pos), line, font=font_bold, fill='black')
            y_pos += line_height
        
        # Draw company if exists
        if company:
            y_pos += 10  # Small gap between name and company
            for line in company_lines:
                bbox = draw.textbbox((0, 0), line, font=font_regular)
                text_width = bbox[2] - bbox[0]
                x_pos = (self.LABEL_WIDTH - text_width) // 2
                draw.text((x_pos, y_pos), line, font=font_regular, fill='black')
                y_pos += company_line_height
        
        # Save image
        temp_filename = f"label_{ticket_data['qr_code'].replace('/', '_')}.png"
        temp_path = os.path.join(settings.BASE_DIR, 'temp', temp_filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        img.save(temp_path)
        
        return temp_path
    
    def _wrap_text(self, text: str, font: ImageFont, max_width: int) -> list:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []
        
        # Create temporary image for text measurement
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, force it
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]  # Return at least the original text
    
    def _send_to_printer(self, image_path: str) -> bool:
        """Send image to printer using TSCLIB."""
        try:
            # TSCLIB commands
            self.tsclibrary.openport.argtypes = [ctypes.c_char_p]
            self.tsclibrary.openport(self.printer_name.encode('utf-8'))
            
            self.tsclibrary.sendcommand(b"SIZE 40 mm, 80 mm")
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
            
            logger.info(f"Successfully sent to printer {self.printer_name} from {image_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send to printer {self.printer_name}: {e}"
            logger.error(error_msg)
            # Log to database for user visibility
            try:
                from ..models import Log
                Log.objects.create(
                    event_type='ERROR',
                    message=f'Print failed: {error_msg}'
                )
            except:
                pass  # Don't fail if logging fails
            return False