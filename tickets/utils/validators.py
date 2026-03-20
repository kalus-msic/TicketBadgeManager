import re
from typing import Optional
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email


def validate_qr_code(qr_code: str) -> bool:
    """Validate QR code format."""
    if not qr_code:
        return False
    
    # Remove whitespace
    qr_code = qr_code.strip()
    
    # Check length (reasonable limits)
    if len(qr_code) < 5 or len(qr_code) > 200:
        return False
    
    # Check for invalid characters (basic sanitization)
    if re.search(r'[<>\"\'%;()&+]', qr_code):
        return False
    
    return True


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return True  # Empty email is allowed
    
    try:
        django_validate_email(email)
        return True
    except ValidationError:
        return False


def sanitize_string(value: str, max_length: int = 200) -> str:
    """Sanitize string input."""
    if not value:
        return ''
    
    # Remove dangerous characters
    value = re.sub(r'[<>\"\'%;()&+]', '', value)
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def validate_csv_file(file):
    """Validate uploaded CSV file."""
    if not file:
        raise ValidationError("No file provided")

    # Check file extension
    if not file.name.endswith('.csv'):
        raise ValidationError("File must be a CSV")

    # Check file size (10MB limit)
    if file.size > 10 * 1024 * 1024:
        raise ValidationError("File size must be less than 10MB")

    # Try to read first few bytes to verify it's text
    try:
        file.seek(0)
        sample = file.read(1024)
        file.seek(0)

        # Try to decode as UTF-8
        sample.decode('utf-8-sig')
    except Exception:
        raise ValidationError("File must be a valid UTF-8 encoded CSV")

    return True


def validate_merge_file(file):
    """Validate uploaded file for merge import. Accepts .csv and .xlsx."""
    if not file:
        raise ValidationError("No file provided")

    allowed_extensions = ('.csv', '.xlsx')
    if not file.name.lower().endswith(allowed_extensions):
        raise ValidationError(f"File must be CSV or XLSX (got: {file.name})")

    if file.size > 10 * 1024 * 1024:
        raise ValidationError("File size must be less than 10MB")

    if file.name.lower().endswith('.csv'):
        try:
            file.seek(0)
            sample = file.read(1024)
            file.seek(0)
            sample.decode('utf-8-sig')
        except Exception:
            raise ValidationError("CSV file must be valid UTF-8 encoded text")

    return True