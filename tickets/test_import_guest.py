import re
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from tickets.models import Event, Ticket
from tickets.forms import TicketForm


class FormGeneratorTests(TestCase):
    def test_form_generates_guest_code(self):
        code = TicketForm()._generate_qr_code()
        self.assertTrue(re.fullmatch(r"GUEST-[A-Z2-9]{8}", code), code)


class ImportGuestModeTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="E", date=timezone.now().date())
        User = get_user_model()
        self.user = User.objects.create_superuser("admin", "a@a.cz", "pw")
        self.client = Client()
        self.client.force_login(self.user)

    def _seed_cache(self, rows, fieldnames):
        session_key = "testkey"
        cache.set(f"import_{session_key}", {"fieldnames": fieldnames, "rows": rows}, 3600)
        return session_key

    def test_import_without_qr_column_generates_guest_codes(self):
        rows = [{"Jmeno": "Alice", "Email": "alice@x.cz"},
                {"Jmeno": "Bob", "Email": "bob@x.cz"}]
        session_key = self._seed_cache(rows, ["Jmeno", "Email"])
        url = reverse("tickets:import_execute", kwargs={"event_pk": self.event.pk})
        # mapping_0 -> name (Jmeno), mapping_1 -> email (Email); zadny qr_code
        resp = self.client.post(url, {
            "session_key": session_key,
            "import_mode": "replace",
            "mapping_0": "name",
            "mapping_1": "email",
        })
        self.assertEqual(Ticket.objects.filter(event=self.event).count(), 2)
        for t in Ticket.objects.filter(event=self.event):
            self.assertTrue(re.fullmatch(r"GUEST-[A-Z2-9]{8}", t.qr_code), t.qr_code)

    def test_append_dedup_by_email(self):
        Ticket.objects.create(qr_code="GUEST-EXIST001", name="Alice",
                              email="alice@x.cz", event=self.event)
        rows = [{"Jmeno": "Alice2", "Email": "alice@x.cz"}]
        session_key = self._seed_cache(rows, ["Jmeno", "Email"])
        url = reverse("tickets:import_execute", kwargs={"event_pk": self.event.pk})
        self.client.post(url, {
            "session_key": session_key,
            "import_mode": "append",
            "mapping_0": "name",
            "mapping_1": "email",
        })
        # Nesmi vzniknout druha vstupenka pro stejny email v ramci eventu
        self.assertEqual(
            Ticket.objects.filter(event=self.event, email__iexact="alice@x.cz").count(), 1)
