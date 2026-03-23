import base64
import logging

from .profiles.tspl import TSPLProfile
from .backends.direct import DirectBackend

logger = logging.getLogger(__name__)


class PrintManager:
    """Routes print jobs to the correct backend based on event settings."""

    def __init__(self, event):
        self._event = event
        self._backend_type = event.print_backend
        self._profile = TSPLProfile()
        self._backend = self._resolve_backend()

    def _resolve_backend(self):
        if self._event.print_backend == "direct":
            return DirectBackend()
        # webusb and agent don't need a server-side backend instance
        return None

    def get_printer_name(self, printer_queue: str) -> str:
        if printer_queue == "1":
            return self._event.printer_1_name or "TDP-2251"
        return self._event.printer_2_name or "TDP-2252"

    def print_ticket(self, ticket_data: dict, printer_queue: str = "1") -> dict:
        """Generate print data and dispatch to the appropriate backend.

        Returns:
            dict with:
                status: "printed" | "print_required" | "error"
                For "print_required": backend, data (base64), printer
                For "error": message
        """
        printer_name = self.get_printer_name(printer_queue)
        backend_type = self._backend_type

        if backend_type == "direct":
            if self._backend is None:
                return {'status': 'error', 'message': 'Direct backend not available'}
            try:
                img = self._profile.generate_image(ticket_data)
            except Exception as e:
                logger.error(f"Image generation failed: {e}")
                return {'status': 'error', 'message': str(e)}
            return self._backend.print_image(img, printer_name)

        # WebUSB and Agent — generate raw byte stream for USB transmission
        try:
            tspl_bytes = self._profile.generate(ticket_data)
        except Exception as e:
            logger.error(f"Profile generation failed: {e}")
            return {'status': 'error', 'message': str(e)}

        return {
            'status': 'print_required',
            'backend': backend_type,
            'data': base64.b64encode(tspl_bytes).decode('ascii'),
            'printer': printer_name,
        }

    def generate_test_print(self, printer_queue: str = "1") -> dict:
        """Generate a test print job."""
        return self.print_ticket({
            'name': 'Test Print',
            'company_name': 'TicketBadgeManager',
            'qr_code': 'TEST',
            'event_name': self._event.name,
        }, printer_queue)
