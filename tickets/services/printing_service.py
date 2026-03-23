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
    
    # Label printing configuration from original
    PWIDTH = 40
    PHEIGHT = 80
    DPI = 200
    DENSITY = 15
    DOT = DPI // 100 * 4
    CONTRAST = 128
    
    # Label size - based on original working code
    # These values match the original create_label_image function
    LABEL_WIDTH = 946
    LABEL_HEIGHT = 572
    MARGIN = 30
    
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
    
    def print_ticket(self, ticket_data: dict, printer_queue: str = "1", event=None) -> bool:
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
            success = self._send_to_printer(image_path, printer_queue, event=event)
            
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
        
        # Create blank image - grayscale like in original
        img = Image.new('L', (self.LABEL_WIDTH, self.LABEL_HEIGHT), 'white')
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        font_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "fonts"
        )
        
        # Get text to display
        name = ticket_data.get('name', '')
        company = ticket_data.get('company_name', '')
        qr_code = ticket_data.get('qr_code', '')
        
        # Start with font size from original
        font_size = 250
        margin = 30
        
        try:
            font_name = ImageFont.truetype(
                os.path.join(font_path, "MontserratBold700.ttf"), 
                font_size
            )
            font_company = None
            if company:
                font_company = ImageFont.truetype(
                    os.path.join(font_path, "MontserratSemiBold600.ttf"), 
                    int(font_size * 0.70)
                )
        except Exception as e:
            logger.error(f"Font loading error: {e}")
            font_name = ImageFont.load_default()
            font_company = ImageFont.load_default() if company else None
        
        # First check if text needs wrapping
        def check_text_width(text, font, max_width):
            """Check if text fits in one line."""
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0] <= max_width
        
        # Only wrap if text is too wide
        available_width = img.width - 2*margin
        if check_text_width(name, font_name, available_width):
            wrap_name = [name]  # Keep on single line
        else:
            wrap_name = textwrap.wrap(name, width=18)
            
        if company:
            if check_text_width(company, font_company, available_width):
                wrap_company = [company]  # Keep on single line
            else:
                wrap_company = textwrap.wrap(company, width=20)
        else:
            wrap_company = []
        
        def get_text_size(text, font):
            """Get text size like in original."""
            lines = text.split('\n')
            widths = [draw.textbbox((0, 0), line, font=font)[2] for line in lines]
            metrics = font.getmetrics()
            heights = [metrics[0] + metrics[1] for line in lines]
            return max(widths), sum(heights)
        
        def txt_size(lines, font):
            """Get size of wrapped lines."""
            return get_text_size("\n".join(lines), font)
        
        name_w, name_h = txt_size(wrap_name, font_name)
        comp_w, comp_h = txt_size(wrap_company, font_company) if company else (0, 0)
        
        # Reduce font size until it fits like in original
        while (name_w > img.width - 2*margin or 
               comp_w > img.width - 2*margin or 
               name_h + comp_h > img.height - 2*margin):
            font_size -= 1
            font_name = ImageFont.truetype(
                os.path.join(font_path, "MontserratBold700.ttf"), 
                font_size
            )
            if company:
                font_company = ImageFont.truetype(
                    os.path.join(font_path, "MontserratSemiBold600.ttf"), 
                    int(font_size * 0.70)
                )
            
            # Re-check if wrapping is needed with new font size
            if check_text_width(name, font_name, available_width):
                wrap_name = [name]
            else:
                wrap_name = textwrap.wrap(name, width=18)
                
            if company:
                if check_text_width(company, font_company, available_width):
                    wrap_company = [company]
                else:
                    wrap_company = textwrap.wrap(company, width=20)
            
            name_w, name_h = txt_size(wrap_name, font_name)
            if company:
                comp_w, comp_h = txt_size(wrap_company, font_company)
        
        # Calculate vertical centering like in original
        y = (img.height - (name_h + comp_h)) / 2
        
        # Draw name lines - centered horizontally
        for line in wrap_name:
            # Get exact text width for centering
            bbox = draw.textbbox((0, 0), line, font=font_name)
            line_width = bbox[2] - bbox[0]
            # Center horizontally - ensure we're truly centered
            x = (img.width - line_width) / 2
            # Make sure we don't go outside margins
            x = max(x, margin)
            draw.text((x, y), line, fill="black", font=font_name)
            # Use font metrics for line height like in original
            metrics = font_name.getmetrics()
            y += metrics[0] + metrics[1]
        
        # Draw company lines if exists
        if company:
            for line in wrap_company:
                # Get exact text width for centering
                bbox = draw.textbbox((0, 0), line, font=font_company)
                line_width = bbox[2] - bbox[0]
                # Center horizontally
                x = (img.width - line_width) / 2
                # Make sure we don't go outside margins
                x = max(x, margin)
                draw.text((x, y), line, fill="black", font=font_company)
                metrics = font_company.getmetrics()
                y += metrics[0] + metrics[1]
        
        # Rotate image 90 degrees like in original
        img = img.rotate(90, expand=True)
        
        # Save image with QR in filename like original
        temp_dir = os.path.join(settings.BASE_DIR, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_filename = f"{name}-{qr_code}.png".replace('/', '_')
        temp_path = os.path.join(temp_dir, temp_filename)
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
    
    def _send_to_printer(self, image_path: str, printer_queue: str = "1", event=None) -> bool:
        """Send image to printer using TSCLIB."""
        try:
            # Resolve printer name from event, fall back to default
            if event:
                printer_name = event.printer_1_name if printer_queue == "1" else event.printer_2_name
            else:
                printer_name = f"TDP-225{printer_queue}"

            # Check if printer exists
            import win32print
            printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
            if printer_name not in printers:
                logger.error(f"Printer {printer_name} not found")
                return False
            
            # Use wide character functions like in original
            self.tsclibrary.openportW(printer_name)
            self.tsclibrary.sendcommandW(f"DENSITY {self.DENSITY}")
            self.tsclibrary.sendcommandW(f"SIZE {self.PWIDTH} mm, {self.PHEIGHT} mm")
            self.tsclibrary.clearbuffer()
            self.tsclibrary.sendcommandW("CLS")
            
            # Call the printOnTop function equivalent with left position 0
            self._print_on_top(image_path, 0)
            
            # Print
            self.tsclibrary.printlabelW("1", "1")
            self.tsclibrary.closeport()
            
            logger.info(f"Successfully sent to printer {printer_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send to printer: {e}"
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
    
    def _print_on_top(self, image_path: str, position: int):
        """Print image on top of label like in original printOnTop function."""
        self._print_pic(image_path, position, 65, 1)
    
    def _print_pic(self, image_path: str, x: int, y: int, mode: int):
        """Print picture using BITMAP command exactly like in original."""
        print(f"PRINTING {image_path}")
        im = Image.open(image_path)
        im.thumbnail((self.PWIDTH * self.DOT, self.PHEIGHT * self.DOT), Image.LANCZOS)
        width, height = im.size
        
        if width < 248:
            print("FAILURE: IMAGE IS TOO SMALL\n")
            logger.error(f"Image is too small: {width}x{height}")
            return -1
        
        # Convert to grayscale
        im = im.convert("L")
        data = list(im.getdata())
        
        # Convert to binary bitmap exactly like original
        im1 = [1 if d >= self.CONTRAST else 0 for d in data]
        bitmap = [0 for _ in range(width * height // 8)]
        offset = [255 for _ in range(width * height // 8)]
        
        for i in range(width * height // 8):
            bits = im1[i*8:(i+1)*8]
            # Convert 8 bits to a byte using eval like in original
            binary_str = "0b" + "".join(str(bit) for bit in bits)
            bitmap[i] = eval(binary_str)
            if bitmap[i] == 0:
                bitmap[i] = 1
                offset[i] = 254
        
        # Send BITMAP command exactly like original
        ini = f"BITMAP {x},{y},{width // 8},{height},{mode},"
        ini_bytes = ini.encode()
        bm = bytes(bitmap)
        ofs = bytes(offset)
        end = b"\0"
        # Use sendcommand (not W) for binary data
        self.tsclibrary.sendcommand(ini_bytes + bm + end)
        self.tsclibrary.sendcommand(ini_bytes + ofs + end)