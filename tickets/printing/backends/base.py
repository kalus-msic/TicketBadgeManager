from abc import ABC, abstractmethod


class AbstractBackend(ABC):
    """Base class for print backends.

    Backends implement ONE of:
    - print_image(img, printer_name) -> dict — for PIL Image (DirectBackend via TSCLIB)
    - print(tspl_bytes, printer_name) -> dict — for raw byte stream (future WebUSB/Agent)

    The unimplemented method raises NotImplementedError.
    PrintManager calls the correct method based on the backend type.
    All backends must implement is_available().
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
