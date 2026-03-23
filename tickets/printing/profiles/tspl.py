import os
import logging
import textwrap
from PIL import Image, ImageDraw, ImageFont

from .base import AbstractPrinterProfile

logger = logging.getLogger(__name__)


class TSPLProfile(AbstractPrinterProfile):
    """TSC Printer Language profile — generates TSPL commands with bitmap data."""

    # Label configuration
    PWIDTH = 40
    PHEIGHT = 80
    DPI = 200
    DENSITY = 15
    DOT = DPI // 100 * 4
    CONTRAST = 128

    # Label image size
    LABEL_WIDTH = 946
    LABEL_HEIGHT = 572
    MARGIN = 30

    # Bitmap position
    BITMAP_X = 0
    BITMAP_Y = 65

    def generate(self, ticket_data: dict) -> bytes:
        """Generate complete TSPL byte stream for USB/network transmission."""
        img = self.generate_image(ticket_data)
        return self._image_to_tspl(img)

    def generate_image(self, ticket_data: dict) -> Image.Image:
        """Generate rotated label image. Used by DirectBackend for TSCLIB.dll."""
        img = self._create_label_image(ticket_data)
        return img.rotate(90, expand=True)

    def generate_test_page(self) -> bytes:
        """Generate a test label with sample data."""
        return self.generate({
            'name': 'Test Print',
            'company_name': 'TicketBadgeManager',
            'qr_code': 'TEST',
            'event_name': 'Test'
        })

    def _create_label_image(self, ticket_data: dict) -> Image.Image:
        """Create label image with name and company text."""
        name = ticket_data.get('name', '')
        company = ticket_data.get('company_name', '')

        img = Image.new('L', (self.LABEL_WIDTH, self.LABEL_HEIGHT), 'white')
        draw = ImageDraw.Draw(img)

        font_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "fonts"
        )

        font_size = 250
        margin = self.MARGIN

        try:
            font_name = ImageFont.truetype(
                os.path.join(font_path, "MontserratBold700.ttf"), font_size
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

        available_width = img.width - 2 * margin

        def check_text_width(text, font, max_width):
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0] <= max_width

        def get_text_size(text, font):
            lines = text.split('\n')
            widths = [draw.textbbox((0, 0), line, font=font)[2] for line in lines]
            metrics = font.getmetrics()
            heights = [metrics[0] + metrics[1] for line in lines]
            return max(widths), sum(heights)

        def txt_size(lines, font):
            return get_text_size("\n".join(lines), font)

        # Wrap text
        if check_text_width(name, font_name, available_width):
            wrap_name = [name]
        else:
            wrap_name = textwrap.wrap(name, width=18)

        if company:
            if check_text_width(company, font_company, available_width):
                wrap_company = [company]
            else:
                wrap_company = textwrap.wrap(company, width=20)
        else:
            wrap_company = []

        name_w, name_h = txt_size(wrap_name, font_name)
        comp_w, comp_h = txt_size(wrap_company, font_company) if company else (0, 0)

        # Auto-shrink font
        while (name_w > img.width - 2 * margin or
               comp_w > img.width - 2 * margin or
               name_h + comp_h > img.height - 2 * margin):
            font_size -= 1
            font_name = ImageFont.truetype(
                os.path.join(font_path, "MontserratBold700.ttf"), font_size
            )
            if company:
                font_company = ImageFont.truetype(
                    os.path.join(font_path, "MontserratSemiBold600.ttf"),
                    int(font_size * 0.70)
                )

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

        # Center vertically
        y = (img.height - (name_h + comp_h)) / 2

        # Draw name
        for line in wrap_name:
            bbox = draw.textbbox((0, 0), line, font=font_name)
            line_width = bbox[2] - bbox[0]
            x = max((img.width - line_width) / 2, margin)
            draw.text((x, y), line, fill="black", font=font_name)
            metrics = font_name.getmetrics()
            y += metrics[0] + metrics[1]

        # Draw company
        if company:
            for line in wrap_company:
                bbox = draw.textbbox((0, 0), line, font=font_company)
                line_width = bbox[2] - bbox[0]
                x = max((img.width - line_width) / 2, margin)
                draw.text((x, y), line, fill="black", font=font_company)
                metrics = font_company.getmetrics()
                y += metrics[0] + metrics[1]

        return img

    def _image_to_tspl(self, img: Image.Image) -> bytes:
        """Convert PIL image to TSPL BITMAP command bytes for USB/network transmission."""
        img = img.copy()
        img.thumbnail((self.PWIDTH * self.DOT, self.PHEIGHT * self.DOT), Image.LANCZOS)
        width, height = img.size

        if width < 248:
            logger.error(f"Image is too small: {width}x{height}")
            raise ValueError(f"Generated image too small: {width}x{height}")

        img = img.convert("L")
        data = list(img.getdata())

        # Convert to binary bitmap (replaces eval("0b...") from original)
        im1 = [1 if d >= self.CONTRAST else 0 for d in data]
        bitmap = [0] * (width * height // 8)
        offset = [255] * (width * height // 8)

        for i in range(width * height // 8):
            bits = im1[i * 8:(i + 1) * 8]
            byte_val = 0
            for bit in bits:
                byte_val = (byte_val << 1) | bit
            if byte_val == 0:
                bitmap[i] = 1
                offset[i] = 254
            else:
                bitmap[i] = byte_val

        # Build TSPL command stream
        parts = []
        parts.append(f"DENSITY {self.DENSITY}\r\n".encode())
        parts.append(f"SIZE {self.PWIDTH} mm, {self.PHEIGHT} mm\r\n".encode())
        parts.append(b"CLS\r\n")

        # BITMAP commands (main + offset layer)
        ini = f"BITMAP {self.BITMAP_X},{self.BITMAP_Y},{width // 8},{height},1,"
        ini_bytes = ini.encode()
        bm = bytes(bitmap)
        ofs = bytes(offset)
        end = b"\0"

        parts.append(ini_bytes + bm + end)
        parts.append(ini_bytes + ofs + end)

        parts.append(b"PRINT 1,1\r\n")

        return b"".join(parts)
