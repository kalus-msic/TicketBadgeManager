import re
from django.test import TestCase
from django.utils import timezone
from tickets.models import Event, Ticket
from tickets.utils.guest_codes import (
    generate_guest_code, existing_qr_codes, GUEST_ALPHABET,
)


class GuestCodeTests(TestCase):
    def test_format(self):
        code = generate_guest_code(set())
        self.assertTrue(re.fullmatch(r"GUEST-[A-Z2-9]{8}", code), code)

    def test_no_ambiguous_chars(self):
        for _ in range(200):
            rand = generate_guest_code(set()).split("-", 1)[1]
            for ch in rand:
                self.assertIn(ch, GUEST_ALPHABET)
                self.assertNotIn(ch, "01OI")

    def test_unique_against_used(self):
        used = set()
        codes = {generate_guest_code(used) for _ in range(500)}
        self.assertEqual(len(codes), 500)
        self.assertEqual(len(used), 500)

    def test_custom_prefix(self):
        self.assertTrue(generate_guest_code(set(), prefix="EV").startswith("EV-"))

    def test_existing_qr_codes_seed(self):
        event = Event.objects.create(name="E", date=timezone.now().date())
        Ticket.objects.create(qr_code="GUEST-ZZZZ9999", name="A", event=event)
        self.assertIn("GUEST-ZZZZ9999", existing_qr_codes())
