import os
import requests
import json
from urllib.parse import urljoin

class APIClient:
    """Client for interacting with the Vinci4D API"""
    
    def __init__(self):
        self.base_url = os.environ.get("BACKEND_ENGINE_URL", "http://localhost:8000")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _url(self, endpoint):
        """Build a full URL from the endpoint"""
        return urljoin(self.base_url, endpoint)
    
    def get(self, endpoint, params=None):
        """Make a GET request to the API"""
        response = requests.get(
            self._url(endpoint),
            params=params,
            headers=self.headers
        )
        return self._handle_response(response)
    
    def post(self, endpoint, data=None, files=None):
        """Make a POST request to the API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if files:
                response = requests.post(url, files=files)
            else:
                # Ensure data is properly serialized as JSON
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, json=data, headers=headers)
            
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def put(self, endpoint, data=None):
        """Make a PUT request to the API"""
        response = requests.put(
            self._url(endpoint),
            json=data,
            headers=self.headers
        )
        return self._handle_response(response)
    
    def delete(self, endpoint, params=None):
        """Make a DELETE request to the API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.delete(url, params=params)
            
            if response.status_code >= 400:
                error_data = response.json() if response.content else {"error": "Unknown error"}
                error_message = error_data.get("error", "Unknown error")
                raise Exception(f"API Error: {error_message}")
            
            # Handle empty responses
            if not response.content or response.content.strip() == b'':
                return {"message": "Operation completed successfully"}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {str(e)}")
        except json.JSONDecodeError:
            # If we can't decode JSON but the status code is OK, consider it a success
            if response.status_code < 400:
                return {"message": "Operation completed successfully"}
            raise Exception("Invalid response from server")
    
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