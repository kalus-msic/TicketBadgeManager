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

    def _svc_email_on(self):
        self.event.eventee_send_email = True
        self.event.save(update_fields=["eventee_send_email"])
        return EventeeService(event=self.event)

    @staticmethod
    def _sent_send_email(req):
        """Precte send_email z posledniho PUT /attendee/invite payloadu."""
        return req.put.call_args.kwargs["json"]["users"][0]["send_email"]

    @patch("tickets.services.eventee_service.requests")
    def test_success_clears_needs_sync(self, req):
        # Prepinac vypnuty (default): data sync, bez e-mailu -> invited zustava False.
        req.put.return_value = _resp(200, {"ok": True})
        t = self._ticket()
        ok, _ = self.svc.sync_ticket(t)
        t.refresh_from_db()
        self.assertTrue(ok)
        self.assertFalse(t.needs_sync)
        self.assertIsNotNone(t.synced_at)
        self.assertEqual(t.eventee_email, "jan@x.cz")
        self.assertFalse(self._sent_send_email(req))
        self.assertFalse(t.invited)

    @patch("tickets.services.eventee_service.requests")
    def test_first_invite_sends_email_and_sets_invited(self, req):
        req.put.return_value = _resp(200, {"ok": True})
        svc = self._svc_email_on()
        t = self._ticket(invited=False)
        svc.sync_ticket(t)
        t.refresh_from_db()
        self.assertTrue(self._sent_send_email(req))
        self.assertTrue(t.invited)

    @patch("tickets.services.eventee_service.requests")
    def test_data_update_does_not_reemail_already_invited(self, req):
        req.put.return_value = _resp(200, {"ok": True})
        svc = self._svc_email_on()
        t = self._ticket(name="New Name", invited=True, eventee_email="jan@x.cz")
        svc.sync_ticket(t)
        t.refresh_from_db()
        self.assertFalse(self._sent_send_email(req))  # jen data update, zadny e-mail
        self.assertTrue(t.invited)

    @patch("tickets.services.eventee_service.requests")
    def test_email_change_reemails(self, req):
        req.put.return_value = _resp(200, {"ok": True})
        req.delete.return_value = _resp(200, {"ok": True})
        svc = self._svc_email_on()
        t = self._ticket(email="new@x.cz", invited=True, eventee_email="old@x.cz")
        svc.sync_ticket(t)
        self.assertTrue(self._sent_send_email(req))  # novy e-mail dostane pozvanku

    @patch("tickets.services.eventee_service.requests")
    def test_put_ok_delete_fail_keeps_needs_sync(self, req):
        # PUT projde, ale DELETE stareho ucastnika selze -> cela operace neuspech:
        # needs_sync zustava True a eventee_email se neposune.
        req.put.return_value = _resp(200, {"ok": True})
        req.delete.return_value = _resp(500, {"err": "x"})
        t = self._ticket(email="new@x.cz", eventee_email="old@x.cz")
        ok, _ = self.svc.sync_ticket(t)
        t.refresh_from_db()
        self.assertFalse(ok)
        self.assertTrue(t.needs_sync)
        self.assertEqual(t.eventee_email, "old@x.cz")

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
