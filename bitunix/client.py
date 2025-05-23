"""
Main client for Bitunix API integration.
"""
import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import json

from .auth import BitunixAuth, DEBUG_SIGNATURE
from .endpoints import MarketEndpoints, AccountEndpoints, PositionEndpoints

load_dotenv()  # Load environment variables from .env file

class BitUnixClient:
    """Main client for interacting with Bitunix API."""
    
    BASE_URL = "https://fapi.bitunix.com"  # Base URL for futures API
    
    def __init__(self):
        """Initialize the client with API credentials and endpoint handlers."""
        self.api_key = os.getenv("BITUNIX_API_KEY")
        self.secret_key = os.getenv("BITUNIX_SECRET_KEY")
        
        self.public_only = False
        if not self.api_key or not self.secret_key:
            print("Warning: API key or secret key not set. Only public endpoints (like klines) will work.")
            self.public_only = True
            self.auth = None
        else:
            self.auth = BitunixAuth(self.api_key, self.secret_key)
        
        # Initialize endpoint handlers
        self.market = MarketEndpoints(self)
        self.account = AccountEndpoints(self)
        self.position = PositionEndpoints(self)
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        is_private: bool = False
    ) -> Any:
        """
        Make a request to the Bitunix API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            is_private: Whether this is a private endpoint requiring authentication
        
        Returns:
            Parsed response data
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        headers: Dict[str, str]
        body_str = ""
        
        if is_private:
            if self.public_only:
                raise ValueError("Cannot call private endpoint without API key and secret.")
            
            # Use auth module to prepare request
            _, body_str, headers = self.auth.prepare_request(method, endpoint, params, data)
        else:
            headers = {"Content-Type": "application/json"}
            if self.api_key:  # Some public endpoints might still benefit from an API key
                headers["api-key"] = self.api_key
            
            # For public endpoints, prepare body if needed
            if data and (method == "POST" or method == "PUT"):
                body_str = json.dumps(data, separators=(',', ':'), sort_keys=True)
        
        # For GET requests, params are in URL, data should be None.
        # For POST/PUT, data is the JSON body, params should generally be None.
        actual_data_for_request = body_str if data is not None and (method == "POST" or method == "PUT") else None
        actual_params_for_request = params if method == "GET" or (method != "GET" and params) else None
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Request] Making {method} request to: {url}")
            print(f"[DEBUG Request] URL Params: {actual_params_for_request}")
            print(f"[DEBUG Request] Request Body: {actual_data_for_request}")
        
        try:
            response = requests.request(
                method,
                url,
                params=actual_params_for_request,
                data=actual_data_for_request,
                headers=headers
            )
            
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Response] Status Code: {response.status_code}")
                print(f"[DEBUG Response] Headers: {response.headers}")
                try:
                    print(f"[DEBUG Response] Text: {response.text[:500]}...")  # Print first 500 chars
                except Exception:
                    print("[DEBUG Response] Could not print response text.")
            
            response.raise_for_status()
            response_data = response.json()
            
            if response_data.get("code") == 0:
                return response_data.get("data")
            else:
                error_message = response_data.get("msg", "Unknown API error")
                print(f"API error for {method} {url}: {error_message} (Code: {response_data.get('code')}) - Response: {response.text}")
                raise requests.exceptions.HTTPError(
                    f"API Error: {error_message} (Code: {response_data.get('code')})",
                    response=response
                )
        
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {http_err.response.text if http_err.response else 'No response text'}")
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            raise
        except json.JSONDecodeError as json_err:
            print(f"JSON decode error for {method} {url}: {json_err}. Response text: {response.text if 'response' in locals() else 'Response object not available'}")
            raise
    
    # Convenience methods that delegate to endpoint handlers
    def get_historical_klines(self, *args, **kwargs):
        """Fetch historical kline data. See MarketEndpoints.get_historical_klines for details."""
        return self.market.get_historical_klines(*args, **kwargs)
    
    def get_account_balance(self, *args, **kwargs):
        """Fetch account balance. See AccountEndpoints.get_account_balance for details."""
        return self.account.get_account_balance(*args, **kwargs)
    
    def get_account_summary(self, *args, **kwargs):
        """Fetch account summary with total values. See AccountEndpoints.get_account_summary for details."""
        return self.account.get_account_summary(*args, **kwargs)
    
    def get_open_positions(self, *args, **kwargs):
        """Fetch open positions. See PositionEndpoints.get_open_positions for details."""
        return self.position.get_open_positions(*args, **kwargs)

    # Remove placeholder example methods
    # def get_example_endpoint(self, params=None):
    #     return self._request("GET", "/v1/example-data", params=params)

    # def post_example_endpoint(self, data=None):
    #     return self._request("POST", "/v1/example-action", data=data) 