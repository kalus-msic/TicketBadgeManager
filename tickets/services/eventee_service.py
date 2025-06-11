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
        
        try:
            # Since most endpoints require event ID in the URL,
            # we can't really test the connection without knowing the event ID
            # Let's try a simple request to see if we get 401 (unauthorized) vs other errors
            
            # Try to access the base API to at least check if token format is correct
            response = requests.get(
                self.API_BASE_URL,  # Just the base URL
                headers=self.headers,
                timeout=self.TIMEOUT
            )
            
            # Even if we get 404, if we don't get 401, the token is at least formatted correctly
            if response.status_code == 401:
                return False, "Invalid API token - authentication failed"
            elif response.status_code == 403:
                return False, "Access forbidden - check API token permissions"
            else:
                # Token seems valid (we didn't get 401)
                return True, "API token appears valid (authentication successful)"
                
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
            # According to the API documentation, we just need the Bearer token
            # The event ID might be associated with the token on Eventee's side
            # or might need to be passed in the request body
            
            data = {
                'email': email,
                'name': name,
                'company': company or ''
            }
            
            # Log the request for debugging
            logger.info(f"Sending invite request to: {self.API_BASE_URL}/attendee/invite")
            logger.info(f"Request data: {data}")
            
            # Try the endpoint as documented
            response = requests.post(
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
            
            if response.status_code in [200, 201]:
                return True, "Invitation sent successfully"
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