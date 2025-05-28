import unicodedata
import re


def normalize_text(text: str) -> str:
    """Normalize text for search - remove diacritics and convert to lowercase."""
    if not text:
        return ''
    
    # Normalize unicode and remove diacritics
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text


def extract_qr_from_url(url: str) -> str:
    """Extract QR code from URL (e.g., https://ti.to/tickets/abc123 -> abc123)."""
    if not url:
        return url
    
    url = url.strip()
    
    # If it's a URL, extract the last part
    if 'http' in url.lower() and '/' in url:
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else url
    
    return url


def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate text to specified length."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_name(first_name: str, last_name: str) -> str:
    """Format name from first and last name."""
    parts = []
    
    if first_name:
        parts.append(first_name.strip())
    
    if last_name:
        parts.append(last_name.strip())
    
    return ' '.join(parts)


def clean_company_name(company: str) -> str:
    """Clean and standardize company name."""
    if not company:
        return ''
    
    company = company.strip()
    
    # Remove common suffixes if they're redundant
    company = re.sub(r'\s+(s\.r\.o\.|a\.s\.|spol\.\s*s\s*r\.o\.)\s*$', '', company, flags=re.IGNORECASE)
    
    return company