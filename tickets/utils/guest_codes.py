import secrets

# Characters without 0/O and 1/I - to avoid ambiguity in manual entry.
GUEST_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GUEST_CODE_LEN = 8
GUEST_PREFIX = "GUEST"


def generate_guest_code(used, prefix=GUEST_PREFIX):
    """Return unique code PREFIX-XXXXXXXX. 'used' is a set of taken codes,
    updated in-place (ensures uniqueness within a batch too)."""
    while True:
        rand = "".join(secrets.choice(GUEST_ALPHABET) for _ in range(GUEST_CODE_LEN))
        code = f"{prefix}-{rand}"
        if code not in used:
            used.add(code)
            return code


def existing_qr_codes():
    """Set of all qr_code from DB - seed for generator (qr_code is globally unique)."""
    from ..models import Ticket
    return set(Ticket.objects.values_list("qr_code", flat=True))
