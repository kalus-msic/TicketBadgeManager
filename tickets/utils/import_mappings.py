"""Import mapping profiles for different ticketing platforms."""

# Mapping profiles for known ticketing platforms
IMPORT_PROFILES = {
    'ti.to': {
        'name': 'ti.to',
        'description': 'Ticketing platform ti.to',
        'mappings': {
            # Column name in CSV -> Model field
            'Ticket First Name': 'name',
            'Ticket Last Name': 'last_name',
            'Ticket Email': 'email',
            'Ticket Company Name': 'company_name',
            'Unique Ticket URL': 'qr_code',
            # Alternative column names (lower priority)
            'Ticket Full Name': 'full_name',  # Special handling needed
        },
        'priority_columns': [
            'Unique Ticket URL',  # Primary QR code source
            'Ticket Reference',   # Fallback QR code
        ],
        'priority_mappings': {
            # If both columns exist, prefer the first one
            'name': ['Ticket First Name', 'Ticket Full Name'],
        }
    },
    
    'simpleshop': {
        'name': 'SimpleShop',
        'description': 'Czech e-commerce platform SimpleShop',
        'mappings': {
            # Column name in CSV -> Model field
            'Kód vstupenky': 'qr_code',
            'Jméno (prodej na jméno)': 'name',
            'Příjmení (prodej na jméno)': 'last_name',
            'E-mail (prodej na jméno)': 'email',
            'Název firmy (prodej na jméno)': 'company_name',
            'Společnost (prodej na jméno)': 'company_name',  # Alternative
            # Fallback mappings
            'ID vstupenky': 'qr_code',  # If Kód vstupenky not available
            'E-mail': 'email',  # If (prodej na jméno) variant not available
        },
        'priority_columns': [
            'Kód vstupenky',
            'ID vstupenky',
        ],
        'priority_mappings': {
            # If both columns exist, prefer the first one
            'email': ['E-mail (prodej na jméno)', 'E-mail'],
        }
    },
    
    'generic_czech': {
        'name': 'Generic Czech CSV',
        'description': 'Generic Czech CSV format',
        'mappings': {
            'Číslo vstupenky': 'qr_code',
            'Jméno': 'name',
            'Příjmení': 'last_name',
            'Firma': 'company_name',
            'Email': 'email',
            'E-mail': 'email',
        }
    },
    
    'generic_english': {
        'name': 'Generic English CSV',
        'description': 'Generic English CSV format',
        'mappings': {
            'Ticket Number': 'qr_code',
            'First Name': 'name',
            'Last Name': 'last_name',
            'Company': 'company_name',
            'Company Name': 'company_name',
            'Email': 'email',
        }
    }
}


def detect_import_profile(fieldnames):
    """
    Detect which import profile to use based on CSV column names.
    Returns profile key or None.
    """
    fieldnames_lower = [f.lower() for f in fieldnames]
    
    # Check for ti.to specific columns
    tito_indicators = ['unique ticket url', 'ticket first name', 'ticket last name', 'ticket email']
    if sum(1 for ind in tito_indicators if ind in fieldnames_lower) >= 3:
        return 'ti.to'
    
    # Check for SimpleShop specific columns
    simpleshop_indicators = ['kód vstupenky', 'položka', 'prodej na jméno']
    if sum(1 for ind in simpleshop_indicators if any(ind in f for f in fieldnames_lower)) >= 2:
        return 'simpleshop'
    
    # Check for Czech generic
    czech_indicators = ['číslo vstupenky', 'jméno', 'příjmení', 'firma']
    if sum(1 for ind in czech_indicators if ind in fieldnames_lower) >= 2:
        return 'generic_czech'
    
    # Default to English generic
    return 'generic_english'


def get_field_mapping_suggestions(fieldnames, samples=None):
    """
    Get field mapping suggestions based on column names and sample data.
    Returns dict of {column_name: suggested_field}.
    """
    # Detect profile
    profile_key = detect_import_profile(fieldnames)
    
    suggestions = {}
    used_fields = set()
    
    if profile_key and profile_key in IMPORT_PROFILES:
        profile = IMPORT_PROFILES[profile_key]
        mappings = profile['mappings']
        
        # Handle priority mappings first
        if 'priority_mappings' in profile:
            for field, priority_columns in profile['priority_mappings'].items():
                for col in priority_columns:
                    if col in fieldnames and field not in used_fields:
                        # Use first available column from priority list
                        if col == 'Ticket Full Name' and 'Ticket First Name' in fieldnames:
                            # Skip Full Name if First Name exists
                            continue
                        suggestions[col] = field
                        used_fields.add(field)
                        break
        
        # First pass: exact matches from profile
        for fieldname in fieldnames:
            if fieldname in mappings and mappings[fieldname] not in used_fields:
                # Skip if already handled by priority mappings
                if fieldname not in suggestions:
                    suggestions[fieldname] = mappings[fieldname]
                    used_fields.add(mappings[fieldname])
        
        # Handle priority columns (for any field that has priority_columns)
        if 'priority_columns' in profile:
            # First, remove any qr_code mappings that might have been set
            qr_code_cols = [col for col, field in suggestions.items() if field == 'qr_code']
            for col in qr_code_cols:
                del suggestions[col]
                if 'qr_code' in used_fields:
                    used_fields.remove('qr_code')
            
            # Then apply priority columns in order
            for priority_col in profile['priority_columns']:
                if priority_col in fieldnames and 'qr_code' not in used_fields:
                    suggestions[priority_col] = 'qr_code'
                    used_fields.add('qr_code')
                    break
    
    # Second pass: fuzzy matching for unmapped columns
    for fieldname in fieldnames:
        if fieldname not in suggestions:
            # Get samples for this specific field
            field_samples = samples.get(fieldname, []) if samples and isinstance(samples, dict) else []
            # Use the original suggestion logic as fallback
            suggestion = _suggest_field_mapping_enhanced(fieldname, field_samples)
            if suggestion and suggestion not in used_fields:
                suggestions[fieldname] = suggestion
                used_fields.add(suggestion)
    
    return suggestions


def _suggest_field_mapping_enhanced(column_name, samples):
    """Enhanced field mapping suggestion with better patterns."""
    column_lower = column_name.lower().strip()
    
    # QR Code patterns - be more specific
    if column_lower in ['unique ticket url', 'ticket reference', 'kód vstupenky', 'číslo vstupenky', 'ticket number', 'id vstupenky']:
        return 'qr_code'
    elif 'qr' in column_lower and 'code' in column_lower:
        return 'qr_code'
    
    # Email patterns
    if 'email' in column_lower or 'e-mail' in column_lower:
        return 'email'
    elif samples and isinstance(samples, list) and any('@' in str(s) for s in samples[:3] if s):
        return 'email'
    
    # Name patterns - be more specific
    if any(x in column_lower for x in ['first name', 'given name', 'forename', 'jméno (prodej']):
        return 'name'
    elif column_lower == 'jméno' or column_lower == 'name':
        return 'name'
    
    # Last name patterns
    if any(x in column_lower for x in ['last name', 'surname', 'family name', 'příjmení (prodej']):
        return 'last_name'
    elif column_lower == 'příjmení':
        return 'last_name'
    
    # Company patterns
    if any(x in column_lower for x in ['company', 'firma', 'organization', 'název firmy', 'společnost']):
        return 'company_name'
    
    return None