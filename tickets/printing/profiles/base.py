from abc import ABC, abstractmethod


class AbstractPrinterProfile(ABC):
    """Base class for printer language profiles."""

    @abstractmethod
    def generate(self, ticket_data: dict) -> bytes:
        """Generate raw byte stream for USB/network transmission.

        Args:
            ticket_data: dict with keys: name, company_name, qr_code, event_name

        Returns:
            Complete byte stream ready to send directly to the printer
            via USB bulk OUT or TCP socket. Used by WebUSB and Agent backends.
        """
        ...

    @abstractmethod
    def generate_image(self, ticket_data: dict) -> 'Image.Image':
        """Generate label image for backends that handle sending themselves.

        Returns:
            PIL Image object (rotated, ready for bitmap conversion).
            Used by DirectBackend which sends via TSCLIB.dll API.
        """
        ...

    @abstractmethod
    def generate_test_page(self) -> bytes:
        """Generate a test page for printer testing."""
        ...
