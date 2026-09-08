from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from tickets.models import Event, Ticket


class ReconcileViewTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name="E", date=timezone.now().date(), eventee_api_token="tok")
        User = get_user_model()
        self.user = User.objects.create_superuser("admin", "a@a.cz", "pw")
        self.client = Client()
        self.client.force_login(self.user)

    @patch("tickets.views.eventee_views.EventeeService")
    def test_report_renders(self, Svc):
        Svc.return_value.reconcile.return_value = {
            "ok": True, "only_in_eventee": [{"email": "ghost@x.cz", "name": "G",
            "first_name": "", "last_name": "", "company": "", "checked_at": None}],
            "missing_in_eventee": [], "cancelled_present": []}
        url = reverse("tickets:reconcile_eventee", kwargs={"event_pk": self.event.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ghost@x.cz")

    @patch("tickets.views.eventee_views.EventeeService")
    def test_apply_imports_only_in_eventee(self, Svc):
        url = reverse("tickets:reconcile_apply", kwargs={"event_pk": self.event.pk})
        resp = self.client.post(url, {"import_email": ["ghost@x.cz"]})
        self.assertEqual(resp.status_code, 302)
        t = Ticket.objects.get(event=self.event, email="ghost@x.cz")
        self.assertTrue(t.qr_code.startswith("EV-"))
        self.assertFalse(t.needs_sync)
        self.assertEqual(t.eventee_email, "ghost@x.cz")
