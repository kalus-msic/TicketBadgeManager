import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings
from ..models import AppSettings

logger = logging.getLogger(__name__)


class EventeeService:
    """Service for handling Eventee API interactions."""
    
    API_BASE_URL = "https://api.eventee.co/v1"
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
            response = requests.get(
                f"{self.API_BASE_URL}/me",
                headers=self.headers,
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                return True, "Connection successful"
            elif response.status_code == 401:
                return False, "Invalid API token"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Connection timeout"
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
            data = {
                'email': email,
                'name': name,
                'company': company or ''
            }
            
            response = requests.post(
                f"{self.API_BASE_URL}/attendees/invite",
                json=data,
                headers=self.headers,
                timeout=self.TIMEOUT
            )
            
            if response.status_code in [200, 201]:
                return True, "Invitation sent successfully"
            elif response.status_code == 409:
                return False, "Attendee already exists"
            else:
                error_msg = response.json().get('message', 'Unknown error')
                return False, f"API error: {error_msg}"
                
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