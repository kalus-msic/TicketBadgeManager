from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from tickets.models import Event


class SyncEventeeViewTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            name="E", date=timezone.now().date(), eventee_api_token="tok")
        User = get_user_model()
        self.user = User.objects.create_superuser("admin", "a@a.cz", "pw")
        self.client = Client()
        self.client.force_login(self.user)

    @patch("tickets.views.eventee_views.EventeeService")
    def test_sync_eventee_calls_service(self, Svc):
        Svc.return_value.sync_event.return_value = {"total": 3, "done": 3, "failed": 0}
        url = reverse("tickets:sync_eventee", kwargs={"event_pk": self.event.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        Svc.return_value.sync_event.assert_called_once_with(self.event)


class SendEmailToggleTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name="E", date=timezone.now().date())
        User = get_user_model()
        self.user = User.objects.create_superuser("admin2", "b@b.cz", "pw")
        self.client = Client()
        self.client.force_login(self.user)

    @patch("tickets.views.settings_views.EventeeService")
    def test_toggle_saved(self, Svc):
        Svc.return_value.test_connection.return_value = (True, "ok")
        url = reverse("tickets:update_eventee_token", kwargs={"event_pk": self.event.pk})
        self.client.post(url, {"api_token": "tok", "eventee_send_email": "on"})
        self.event.refresh_from_db()
        self.assertTrue(self.event.eventee_send_email)

    @patch("tickets.views.settings_views.EventeeService")
    def test_toggle_unchecked_saves_false(self, Svc):
        Svc.return_value.test_connection.return_value = (True, "ok")
        self.event.eventee_send_email = True
        self.event.save(update_fields=["eventee_send_email"])
        url = reverse("tickets:update_eventee_token", kwargs={"event_pk": self.event.pk})
        self.client.post(url, {"api_token": "tok"})  # checkbox not in POST
        self.event.refresh_from_db()
        self.assertFalse(self.event.eventee_send_email)
