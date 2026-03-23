from abc import ABC, abstractmethod


class AbstractBackend(ABC):
    """Base class for print backends.

    Backends implement either:
    - print(tspl_bytes, printer_name) — for raw byte stream (WebUSB, Agent)
    - print_image(img, printer_name) — for PIL Image (DirectBackend via TSCLIB)

    PrintManager calls the appropriate method based on backend type.
    """

    def print(self, tspl_bytes: bytes, printer_name: str) -> dict:
        """Send raw TSPL byte stream to printer. Used by WebUSB/Agent."""
        raise NotImplementedError(f"{type(self).__name__} must implement print()")

    def print_image(self, img, printer_name: str) -> dict:
        """Send PIL image to printer via native API. Used by DirectBackend."""
        raise NotImplementedError(f"{type(self).__name__} must implement print_image()")

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is currently usable."""
        ...
