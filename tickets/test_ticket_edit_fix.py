from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from tickets.models import Event, Ticket


class TicketEditChangeTrackingTests(TestCase):
    """Regression: ticket_edit crashed with AttributeError on the derived
    'event_name' key in the change-tracking loop (getattr(ticket,'event_name'))."""

    def setUp(self):
        self.event = Event.objects.create(name="E", date=timezone.now().date())
        self.ticket = Ticket.objects.create(
            qr_code="GUEST-AAAA1111", name="Old Name",
            company_name="ACME", email="a@a.cz", status="VALID", event=self.event,
        )
        User = get_user_model()
        self.user = User.objects.create_superuser("admin", "a@a.cz", "pw")
        self.client = Client()
        self.client.force_login(self.user)

    def test_edit_ticket_post_redirects_and_saves(self):
        url = reverse("tickets:ticket_edit",
                      kwargs={"event_pk": self.event.pk, "pk": self.ticket.pk})
        resp = self.client.post(url, {
            "qr_code": "GUEST-AAAA1111",
            "name": "New Name",
            "company_name": "ACME",
            "email": "a@a.cz",
            "status": "VALID",
        })
        # Must redirect to detail, not crash with a 500 / error page.
        self.assertEqual(resp.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.name, "New Name")

    @patch("tickets.views.ticket_views.EventeeService")
    def test_edit_reinvites_already_invited_ticket(self, Svc):
        """Editing an already-invited ticket with the invite checkbox checked
        must re-sync it (so a re-send / send_email change reaches Eventee)."""
        Svc.return_value.sync_ticket.return_value = (True, "ok")
        self.ticket.invited = True
        self.ticket.save(update_fields=["invited"])
        url = reverse("tickets:ticket_edit",
                      kwargs={"event_pk": self.event.pk, "pk": self.ticket.pk})
        resp = self.client.post(url, {
            "qr_code": "GUEST-AAAA1111",
            "name": "Old Name",
            "company_name": "ACME",
            "email": "a@a.cz",
            "status": "VALID",
            "invite_to_eventee": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Svc.return_value.sync_ticket.called)
