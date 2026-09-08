from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from tickets.models import Event, Ticket
from tickets.services.eventee_service import EventeeService


class ReconcileTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name="E", date=timezone.now().date(), eventee_api_token="tok")
        self.svc = EventeeService(event=self.event)

    def _ticket(self, **kw):
        base = dict(qr_code="GUEST-AAAA1111", name="Jan", event=self.event)
        base.update(kw)
        return Ticket.objects.create(**base)

    @patch.object(EventeeService, "get_participants")
    def test_only_in_eventee(self, gp):
        gp.return_value = (True, [{"email": "ghost@x.cz", "name": "Ghost"}])
        self._ticket(email="jan@x.cz", eventee_email="jan@x.cz")
        result = self.svc.reconcile(self.event)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["only_in_eventee"]), 1)
        self.assertEqual(result["only_in_eventee"][0]["email"], "ghost@x.cz")

    @patch.object(EventeeService, "get_participants")
    def test_missing_in_eventee(self, gp):
        gp.return_value = (True, [])
        self._ticket(email="jan@x.cz", eventee_email="jan@x.cz")
        result = self.svc.reconcile(self.event)
        self.assertEqual(len(result["missing_in_eventee"]), 1)

    @patch.object(EventeeService, "get_participants")
    def test_cancelled_present(self, gp):
        gp.return_value = (True, [{"email": "jan@x.cz"}])
        self._ticket(email="jan@x.cz", eventee_email="jan@x.cz", status="CANCELLED")
        result = self.svc.reconcile(self.event)
        self.assertEqual(len(result["cancelled_present"]), 1)

    @patch.object(EventeeService, "get_participants")
    def test_failure_propagates(self, gp):
        gp.return_value = (False, "HTTP 401")
        result = self.svc.reconcile(self.event)
        self.assertFalse(result["ok"])
