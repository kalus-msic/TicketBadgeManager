import os
import platform
import ctypes
import logging

from .base import AbstractBackend
from ..profiles.tspl import TSPLProfile

logger = logging.getLogger(__name__)


class DirectBackend(AbstractBackend):
    """Server-side printing via TSCLIB.dll. Requires Windows + DLL on same machine.

    Uses TSCLIB.dll API: sendcommandW() for text commands, sendcommand()
    for binary BITMAP data — matching original PrintingService._send_to_printer.
    """

    # Label configuration — single source of truth from TSPLProfile
    PWIDTH = TSPLProfile.PWIDTH
    PHEIGHT = TSPLProfile.PHEIGHT
    DPI = TSPLProfile.DPI
    DENSITY = TSPLProfile.DENSITY
    DOT = TSPLProfile.DOT
    CONTRAST = TSPLProfile.CONTRAST
    BITMAP_X = TSPLProfile.BITMAP_X
    BITMAP_Y = TSPLProfile.BITMAP_Y

    def __init__(self):
        self._tsclibrary = None
        self._printers_available = []
        if platform.system() == "Windows":
            self._init_windows()

    def _init_windows(self):
        """Load TSCLIB.dll and enumerate local printers."""
        try:
            import win32print
            self._printers_available = [
                p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            ]

            tsclib_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "libs", "TSCLIB.dll"
            )
            if os.path.exists(tsclib_path):
                self._tsclibrary = ctypes.WinDLL(tsclib_path)
                logger.info("TSCLIB.dll loaded successfully")
            else:
                logger.warning(f"TSCLIB.dll not found at {tsclib_path}")
        except ImportError:
            logger.error("win32print module not available")
        except Exception as e:
            logger.error(f"Failed to initialize DirectBackend: {e}")

    def is_available(self) -> bool:
        return platform.system() == "Windows" and self._tsclibrary is not None

    def print_image(self, img, printer_name: str) -> dict:
        """Send PIL image to printer via TSCLIB.dll API calls."""
        if not self._tsclibrary:
            if platform.system() != "Windows":
                return {'status': 'error', 'message': 'TSC thermal printers require Windows with TSCLIB.dll.'}
            return {'status': 'error', 'message': 'TSCLIB.dll not loaded'}

        if printer_name not in self._printers_available:
            return {
                'status': 'error',
                'message': f'Printer {printer_name} not found. '
                           f'Available: {", ".join(self._printers_available)}'
            }

        self._tsclibrary.openportW(printer_name)
        try:
            self._tsclibrary.sendcommandW(f"DENSITY {self.DENSITY}")
            self._tsclibrary.sendcommandW(f"SIZE {self.PWIDTH} mm, {self.PHEIGHT} mm")
            self._tsclibrary.clearbuffer()
            self._tsclibrary.sendcommandW("CLS")
            self._send_bitmap(img, self.BITMAP_X, self.BITMAP_Y)
            self._tsclibrary.printlabelW("1", "1")
            logger.info(f"Successfully sent to printer {printer_name}")
            return {'status': 'printed'}
        except Exception as e:
            logger.error(f"Failed to send to printer: {e}")
            return {'status': 'error', 'message': str(e)}
        finally:
            self._tsclibrary.closeport()

    def _send_bitmap(self, img, x: int, y: int):
        """Convert PIL image to bitmap and send via TSCLIB sendcommand (binary).

        Matches original PrintingService._print_pic logic exactly.
        """
        from PIL import Image as PILImage
        img = img.copy()
        img.thumbnail((self.PWIDTH * self.DOT, self.PHEIGHT * self.DOT), PILImage.LANCZOS)
        width, height = img.size

        if width < 248:
            raise ValueError(f"Image too small after thumbnail: {width}x{height}")

        img = img.convert("L")
        data = list(img.getdata())

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

        ini = f"BITMAP {x},{y},{width // 8},{height},1,"
        ini_bytes = ini.encode()
        bm = bytes(bitmap)
        ofs = bytes(offset)
        end = b"\0"

        self._tsclibrary.sendcommand(ini_bytes + bm + end)
        self._tsclibrary.sendcommand(ini_bytes + ofs + end)

    def print(self, tspl_bytes: bytes, printer_name: str) -> dict:
        """Not used by PrintManager — DirectBackend uses print_image()."""
        raise NotImplementedError("DirectBackend uses print_image(), not print()")
