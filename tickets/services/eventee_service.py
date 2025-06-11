import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings
from ..models import AppSettings

logger = logging.getLogger(__name__)


class EventeeService:
    """Service for handling Eventee API interactions."""
    
    API_BASE_URL = "https://api.eventee.co/public/v1"
    TIMEOUT = 30  # seconds
    
    def __init__(self):
        self.settings = AppSettings.objects.first()
        self.api_token = self.settings.eventee_api_token if self.settings else None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get API headers with authentication."""
        if not self.api_token:
            return {}
        
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test API connection and token validity."""
        if not self.api_token:
            return False, "No API token configured"
        
        # Check if token is just whitespace
        if not self.api_token.strip():
            return False, "API token is empty"
        
        # Since we can't test the API without making a real call,
        # just do basic validation
        if len(self.api_token.strip()) < 10:
            return False, "API token appears too short"
        
        # Always return False to indicate we can't verify
        # This prevents confusion in the UI
        return False, "API token saved but not verified. Authentication will be tested when inviting attendees."
    
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
            if not self.settings:
                self.settings = AppSettings.objects.create(eventee_api_token=token)
            else:
                self.settings.eventee_api_token = token
                self.settings.save()
            
            self.api_token = token
            return True
            
        except Exception as e:
            logger.error(f"Failed to update API token: {e}")
            return False