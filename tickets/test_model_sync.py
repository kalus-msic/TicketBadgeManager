from django.test import TestCase
from django.utils import timezone
from tickets.models import Event, Ticket


class TicketSyncModelTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="E", date=timezone.now().date())

    def test_new_ticket_needs_sync_true(self):
        t = Ticket.objects.create(qr_code="GUEST-AAAA1111", name="A", event=self.event)
        self.assertTrue(t.needs_sync)

    def test_editing_sync_field_sets_needs_sync(self):
        t = Ticket.objects.create(qr_code="GUEST-AAAA2222", name="A", event=self.event)
        t.needs_sync = False
        t.save(update_fields=["needs_sync"])
        t.refresh_from_db()
        self.assertFalse(t.needs_sync)
        t.name = "B"
        t.save()
        t.refresh_from_db()
        self.assertTrue(t.needs_sync)

    def test_bookkeeping_save_does_not_redirty(self):
        t = Ticket.objects.create(qr_code="GUEST-AAAA3333", name="A", event=self.event)
        t.needs_sync = False
        t.synced_at = timezone.now()
        t.save(update_fields=["needs_sync", "synced_at"])
        t.refresh_from_db()
        self.assertFalse(t.needs_sync)

    def test_event_send_email_default_false(self):
        self.assertFalse(self.event.eventee_send_email)

    def test_update_fields_with_sync_field_persists_needs_sync(self):
        # save(update_fields=[sync-field]) must append needs_sync so the flag
        # actually gets written (the trickiest branch of the override).
        t = Ticket.objects.create(qr_code="GUEST-AAAA4444", name="A", event=self.event)
        t.needs_sync = False
        t.save(update_fields=["needs_sync"])
        t.refresh_from_db()
        self.assertFalse(t.needs_sync)
        t.name = "B"
        t.save(update_fields=["name"])
        t.refresh_from_db()
        self.assertEqual(t.name, "B")
        self.assertTrue(t.needs_sync)
