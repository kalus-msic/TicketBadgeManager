from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from tickets.models import Event


class SyncCommandTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name="E", date=timezone.now().date(), eventee_api_token="tok")

    @patch("tickets.management.commands.sync_eventee.EventeeService")
    def test_sync_prints_summary(self, Svc):
        Svc.return_value.sync_event.return_value = {"total": 2, "done": 2, "failed": 0}
        out = StringIO()
        call_command("sync_eventee", str(self.event.pk), stdout=out)
        self.assertIn("done=2", out.getvalue())
        Svc.return_value.sync_event.assert_called_once_with(self.event)
