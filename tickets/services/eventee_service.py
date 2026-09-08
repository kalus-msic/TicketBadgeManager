import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings

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
    
    def invite_attendee(self, email: str, name: str, company: str = '') -> Tuple[bool, str]:
        """Invite an attendee to Eventee."""
        if not self.api_token:
            return False, "No API token configured"
        
        if not email:
            return False, "Email is required"
        
        try:
            # Split name into first and last name
            name_parts = name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Use the exact payload structure that worked before
            data = {
                "users": [
                    {
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                        "send_email": True,
                    }
                ]
            }
            
            # Add company if provided
            if company:
                data["users"][0]["company"] = company
            
            # Log the request for debugging
            logger.info(f"Sending invite request to: {self.API_BASE_URL}/attendee/invite")
            logger.info(f"Request data: {data}")
            
            # Use PUT method as in the working example
            response = requests.put(
                f"{self.API_BASE_URL}/attendee/invite",
                json=data,
                headers=self.headers,
                timeout=self.TIMEOUT
            )
            
            # Log the response for debugging
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            try:
                logger.info(f"Response body: {response.text}")
            except:
                pass
            
            if response.ok:  # This checks for any 2xx status code
                return True, f"Invitation sent successfully: {response.text}"
            elif response.status_code == 409:
                return False, "Attendee already exists"
            elif response.status_code == 401:
                return False, "Invalid API token - authentication failed"
            elif response.status_code == 403:
                return False, "Access forbidden - check API token permissions"
            elif response.status_code == 404:
                # If we get 404, the endpoint might be wrong or need event ID
                return False, "API endpoint not found. The API might require event ID in the URL or request body."
            elif response.status_code == 400:
                # Bad request - missing required fields
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', 'Bad request'))
                    return False, f"Bad request: {error_msg}"
                except:
                    return False, f"Bad request: {response.text}"
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', response.text))
                except:
                    error_msg = response.text
                return False, f"API error {response.status_code}: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout"
        except requests.exceptions.RequestException as e:
            logger.error(f"Eventee invite error: {e}")
            return False, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error inviting to Eventee: {e}")
            return False, "Unexpected error"
    
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