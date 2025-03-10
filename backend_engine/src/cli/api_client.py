import os
import requests
import json
from urllib.parse import urljoin
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from config.env
env_path = Path(__file__).parent.parent.parent.parent / 'config.env'
load_dotenv(env_path)

class APIClient:
    """Client for interacting with the Vinci4D API"""
    
    def __init__(self):
        # Get the backend URL from environment variables
        self.base_url = os.environ.get('BACKEND_ENGINE_URL', 'http://localhost:30001')
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _url(self, endpoint):
        """Build a full URL from the endpoint"""
        return urljoin(self.base_url, endpoint)
    
    def get(self, endpoint, params=None):
        """Make a GET request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.json()
    
    def post(self, endpoint, data=None):
        """Make a POST request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def put(self, endpoint, data=None):
        """Make a PUT request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.put(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint):
        """Make a DELETE request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url)
        response.raise_for_status()
        return response.json()
    
    def _handle_response(self, response):
        """Handle API response and errors"""
        try:
            response.raise_for_status()
            if response.content:
                return response.json()
            return None
        except requests.exceptions.HTTPError as e:
            if response.content:
                error_data = response.json()
                if "error" in error_data:
                    raise Exception(f"API Error: {error_data['error']}")
            raise Exception(f"API Error: {str(e)}")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to the API server. Is it running?")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from the API")
    
    def post_file(self, endpoint, files=None, data=None):
        """Send a POST request with file upload"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        raise Exception(error_data['error'])
                except:
                    pass
            raise Exception(f"API request failed: {str(e)}") 