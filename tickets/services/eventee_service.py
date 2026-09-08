import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class EventeeService:
    """Service for handling Eventee API interactions."""

    API_BASE_URL = settings.EVENTEE_BASE_URL
    TIMEOUT = 30  # seconds

    def __init__(self, event=None):
        if event:
            self.api_token = event.eventee_api_token
        else:
            # Fallback during migration period
            from ..models import AppSettings
            settings_obj = AppSettings.objects.first()
            self.api_token = settings_obj.eventee_api_token if settings_obj else None
        self.send_email = bool(getattr(event, "eventee_send_email", False))

    @property
    def headers(self) -> Dict[str, str]:
        """Get API headers with authentication."""
        if not self.api_token:
            return {}

        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': settings.EVENTEE_USER_AGENT,
        }

    def eventee_email_for(self, ticket):
        """Realny e-mail vstupenky, jinak placeholder vstupenka-<qr>@<domena>."""
        if ticket.email and ticket.email.strip():
            return ticket.email.strip()
        return f"vstupenka-{ticket.qr_code}@{settings.EVENTEE_PLACEHOLDER_DOMAIN}"

    def build_invite_user(self, ticket):
        """Overeny payload tvar (Flask app). Cislo vstupenky = qr_code.
        send_email dle per-event nastaveni (self.send_email). Snake_case -
        camelCase Eventee ignoruje (pak chybi jmeno)."""
        first, _, last = (ticket.name or "").partition(" ")
        user = {
            "email": self.eventee_email_for(ticket),
            "send_email": self.send_email,
            "tickets": [{"number": ticket.qr_code, "title": "", "type": "qr"}],
        }
        if first:
            user["first_name"] = first
        if last:
            user["last_name"] = last
        if ticket.company_name:
            user["company"] = ticket.company_name
        return user

    def plan_ticket_sync(self, ticket):
        """Rozhodne operace pro jednu vstupenku. Vraci dict s klici
        invite_email, delete_email, user."""
        target = self.eventee_email_for(ticket)
        old = (ticket.eventee_email or "").strip() or None
        if ticket.status == "CANCELLED":
            return {"invite_email": None, "delete_email": old, "user": None}
        plan = {"invite_email": target, "delete_email": None,
                "user": self.build_invite_user(ticket)}
        if old and old.lower() != target.lower():
            plan["delete_email"] = old
        return plan

    def _put_invite(self, users):
        """Vraci (status, ok, detail). ok = HTTP 200 A telo je JSON dict."""
        resp = requests.put(
            f"{self.API_BASE_URL}/attendee/invite",
            json={"users": users}, headers=self.headers, timeout=self.TIMEOUT,
        )
        try:
            body = resp.json()
        except ValueError:
            body = None
        ok = resp.status_code == 200 and isinstance(body, dict)
        detail = body if isinstance(body, dict) else "non-json body"
        return resp.status_code, ok, detail

    def _delete_attendee(self, email):
        """Vraci (status, ok). ok = HTTP 200 nebo 204."""
        resp = requests.delete(
            f"{self.API_BASE_URL}/attendee",
            json={"email": email}, headers=self.headers, timeout=self.TIMEOUT,
        )
        return resp.status_code, resp.status_code in (200, 204)

    def sync_ticket(self, ticket):
        """Synchronizuje jednu vstupenku dle planu. Vraci (ok, log_text)."""
        if not self.api_token:
            return False, "No API token configured"
        plan = self.plan_ticket_sync(ticket)
        logs = []
        ok = True
        try:
            if plan["user"] is not None:
                status, put_ok, detail = self._put_invite([plan["user"]])
                if put_ok:
                    logs.append(f"PUT invite {plan['invite_email']}: OK")
                else:
                    ok = False
                    logs.append(f"PUT invite {plan['invite_email']}: HTTP {status} {detail}")
            if plan["delete_email"] and ok:
                dstatus, dok = self._delete_attendee(plan["delete_email"])
                logs.append(f"DELETE {plan['delete_email']}: {'OK' if dok else 'HTTP ' + str(dstatus)}")
                if not dok:
                    ok = False
        except requests.exceptions.RequestException as e:
            ok = False
            logs.append(f"Request error: {e}")

        log_text = "\n".join(logs)
        if ok:
            ticket.needs_sync = False
            ticket.synced_at = timezone.now()
            ticket.sync_log = log_text
            if plan["invite_email"]:
                ticket.eventee_email = plan["invite_email"]
                ticket.invited = True
            elif plan["delete_email"]:
                ticket.eventee_email = None
            ticket.save(update_fields=[
                "needs_sync", "synced_at", "sync_log", "eventee_email", "invited",
            ])
        else:
            ticket.sync_log = log_text
            ticket.save(update_fields=["sync_log"])
        return ok, log_text

    def sync_event(self, event):
        """Posle vsechny needs_sync vstupenky eventu (per-ticket). Vraci
        {total, done, failed}."""
        tickets = event.tickets.filter(needs_sync=True)
        total = tickets.count()
        done = failed = 0
        for ticket in tickets:
            ok, _ = self.sync_ticket(ticket)
            if ok:
                done += 1
            else:
                failed += 1
        return {"total": total, "done": done, "failed": failed}

    def get_participants(self):
        """GET /participants -> (ok, list) nebo (False, detail)."""
        if not self.api_token:
            return False, "No API token configured"
        try:
            resp = requests.get(
                f"{self.API_BASE_URL}/participants",
                headers=self.headers, timeout=self.TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {e}"
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        try:
            data = resp.json()
        except ValueError:
            return False, "Invalid response body"
        if not isinstance(data, list):
            return False, "Unexpected response (not a list)"
        return True, data

    def reconcile(self, event):
        """Porovna Eventee ucastniky s lokalni DB (jen tento event).
        Vraci dict s kategoriemi rozdilu."""
        ok, data = self.get_participants()
        if not ok:
            return {"ok": False, "detail": data,
                    "only_in_eventee": [], "missing_in_eventee": [],
                    "cancelled_present": []}

        ev = {}
        for p in data:
            email = (p.get("email") or "").strip().lower()
            if email:
                ev[email] = p

        app_all = set()
        synced = {}
        for t in event.tickets.all():
            if t.eventee_email:
                e = t.eventee_email.strip().lower()
                app_all.add(e)
                synced[e] = t
            if t.email:
                app_all.add(t.email.strip().lower())
            if t.status != "CANCELLED":
                app_all.add(self.eventee_email_for(t).lower())

        only_in_eventee = [
            {"email": e,
             "name": ev[e].get("name") or "",
             "first_name": ev[e].get("first_name") or "",
             "last_name": ev[e].get("last_name") or "",
             "company": ev[e].get("company") or "",
             "checked_at": ev[e].get("checked_at")}
            for e in ev if e not in app_all
        ]
        missing_in_eventee = [
            {"qr_code": t.qr_code, "email": e}
            for e, t in synced.items() if e not in ev and t.status != "CANCELLED"
        ]
        cancelled_present = [
            {"qr_code": t.qr_code, "email": e}
            for e, t in synced.items() if e in ev and t.status == "CANCELLED"
        ]
        return {"ok": True,
                "eventee_total": len(ev), "app_synced_total": len(synced),
                "only_in_eventee": only_in_eventee,
                "missing_in_eventee": missing_in_eventee,
                "cancelled_present": cancelled_present}

    def test_connection(self) -> Tuple[bool, str]:
        """Test API connection and token validity."""
        if not self.api_token:
            return False, "No API token configured"
        
        # Check if token is just whitespace
        if not self.api_token.strip():
            return False, "API token is empty"
        
        try:
            # Test the API token with GET request to content endpoint
            response = requests.get(
                f"{self.API_BASE_URL}/content",
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Accept': 'application/json'
                },
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                return True, "API token verified successfully"
            elif response.status_code == 401:
                return False, "Invalid API token - authentication failed"
            elif response.status_code == 403:
                return False, "Access forbidden - check API token permissions"
            else:
                return False, f"API test failed with status code: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Connection timeout - API might be unreachable"
        except requests.exceptions.RequestException as e:
            logger.error(f"Eventee API connection error: {e}")
            return False, f"Connection error: {str(e)}"
    
    def update_api_token(self, token: str) -> bool:
        """Update API token in settings."""
        try:
            from ..models import AppSettings
            settings_obj = AppSettings.objects.first()
            if not settings_obj:
                AppSettings.objects.create(eventee_api_token=token)
            else:
                settings_obj.eventee_api_token = token
                settings_obj.save()

            self.api_token = token
            return True

        except Exception as e:
            logger.error(f"Failed to update API token: {e}")
            return False