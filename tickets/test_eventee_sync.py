from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.utils import timezone
from tickets.models import Event, Ticket
from tickets.services.eventee_service import EventeeService


def _resp(status, json_body=None):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_body if json_body is not None else {}
    return m


class SyncTicketTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name="E", date=timezone.now().date(), eventee_api_token="tok")
        self.svc = EventeeService(event=self.event)

    def _ticket(self, **kw):
        base = dict(qr_code="GUEST-AAAA1111", name="Jan", email="jan@x.cz", event=self.event)
        base.update(kw)
        return Ticket.objects.create(**base)

    @patch("tickets.services.eventee_service.requests")
    def test_success_clears_needs_sync(self, req):
        req.put.return_value = _resp(200, {"ok": True})
        t = self._ticket()
        ok, _ = self.svc.sync_ticket(t)
        t.refresh_from_db()
        self.assertTrue(ok)
        self.assertFalse(t.needs_sync)
        self.assertIsNotNone(t.synced_at)
        self.assertEqual(t.eventee_email, "jan@x.cz")
        self.assertTrue(t.invited)

    @patch("tickets.services.eventee_service.requests")
    def test_html_body_is_failure(self, req):
        r = _resp(200)
        r.json.side_effect = ValueError("no json")
        req.put.return_value = r
        t = self._ticket()
        ok, _ = self.svc.sync_ticket(t)
        t.refresh_from_db()
        self.assertFalse(ok)
        self.assertTrue(t.needs_sync)

    @patch("tickets.services.eventee_service.requests")
    def test_email_change_calls_delete(self, req):
        req.put.return_value = _resp(200, {"ok": True})
        req.delete.return_value = _resp(200, {"ok": True})
        t = self._ticket(email="new@x.cz", eventee_email="old@x.cz")
        ok, _ = self.svc.sync_ticket(t)
        self.assertTrue(ok)
        req.delete.assert_called_once()

    @patch("tickets.services.eventee_service.requests")
    def test_sync_event_counts(self, req):
        req.put.return_value = _resp(200, {"ok": True})
        self._ticket(qr_code="GUEST-BBBB2222")
        self._ticket(qr_code="GUEST-CCCC3333")
        result = self.svc.sync_event(self.event)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["done"], 2)
        self.assertEqual(result["failed"], 0)
