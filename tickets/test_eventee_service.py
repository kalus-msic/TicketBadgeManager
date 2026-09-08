from django.test import TestCase, override_settings
from django.utils import timezone
from tickets.models import Event, Ticket
from tickets.services.eventee_service import EventeeService


@override_settings(EVENTEE_PLACEHOLDER_DOMAIN="vstupenka.local")
class BuilderTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name="E", date=timezone.now().date(), eventee_api_token="tok")
        self.svc = EventeeService(event=self.event)

    def _ticket(self, **kw):
        base = dict(qr_code="GUEST-AAAA1111", name="Jan Novak", event=self.event)
        base.update(kw)
        return Ticket.objects.create(**base)

    def test_email_real(self):
        t = self._ticket(email="jan@x.cz")
        self.assertEqual(self.svc.eventee_email_for(t), "jan@x.cz")

    def test_email_placeholder(self):
        t = self._ticket(email=None)
        self.assertEqual(self.svc.eventee_email_for(t),
                         "vstupenka-GUEST-AAAA1111@vstupenka.local")

    def test_build_user_payload(self):
        t = self._ticket(email="jan@x.cz", company_name="ACME")
        user = self.svc.build_invite_user(t)
        self.assertEqual(user["email"], "jan@x.cz")
        self.assertFalse(user["send_email"])  # default event flag False
        self.assertEqual(user["first_name"], "Jan")
        self.assertEqual(user["last_name"], "Novak")
        self.assertEqual(user["company"], "ACME")
        self.assertEqual(user["tickets"], [{"number": "GUEST-AAAA1111", "title": "", "type": "qr"}])

    def test_send_email_from_event_flag(self):
        self.event.eventee_send_email = True
        self.event.save(update_fields=["eventee_send_email"])
        svc = EventeeService(event=self.event)
        user = svc.build_invite_user(self._ticket(email="j2@x.cz"))
        self.assertTrue(user["send_email"])

    def test_plan_normal(self):
        t = self._ticket(email="jan@x.cz")
        plan = self.svc.plan_ticket_sync(t)
        self.assertEqual(plan["invite_email"], "jan@x.cz")
        self.assertIsNone(plan["delete_email"])

    def test_plan_email_change_deletes_old(self):
        t = self._ticket(email="new@x.cz", eventee_email="old@x.cz")
        plan = self.svc.plan_ticket_sync(t)
        self.assertEqual(plan["invite_email"], "new@x.cz")
        self.assertEqual(plan["delete_email"], "old@x.cz")

    def test_plan_cancelled_synced_deletes(self):
        t = self._ticket(email="jan@x.cz", eventee_email="jan@x.cz", status="CANCELLED")
        plan = self.svc.plan_ticket_sync(t)
        self.assertIsNone(plan["invite_email"])
        self.assertEqual(plan["delete_email"], "jan@x.cz")

    def test_plan_cancelled_never_synced_local_only(self):
        t = self._ticket(email="jan@x.cz", status="CANCELLED")
        plan = self.svc.plan_ticket_sync(t)
        self.assertIsNone(plan["invite_email"])
        self.assertIsNone(plan["delete_email"])
