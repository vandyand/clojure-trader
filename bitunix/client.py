import os
import requests
from dotenv import load_dotenv
from typing import List, NamedTuple, Optional, Dict, Any
import hashlib # For SHA256
import time    # For timestamp
import json    # For json.dumps to create request body string for signature
import uuid    # For nonce generation

# Enable detailed logging for debugging
DEBUG_SIGNATURE = True # Set to False to disable verbose signature logging

load_dotenv() # Load environment variables from .env file

# Define a data structure for Candlestick data
class Candlestick(NamedTuple):
    open_time: int  # Start time of the candle (Unix timestamp in ms)
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float      # Trading volume (base asset, e.g., BTC for BTCUSDT)
    quote_volume: float # Trading amount (quote asset, e.g., USDT for BTCUSDT)
    kline_type: Optional[str] = None # e.g., LAST_PRICE or MARK_PRICE

class AccountBalance(NamedTuple):
    margin_coin: str
    available: float # Available quantity
    frozen: float    # Locked quantity for orders
    margin: float    # Locked quantity for positions
    transfer: float  # Maximum transferable amount
    position_mode: str # ONE_WAY or HEDGE
    cross_unrealized_pnl: float
    isolation_unrealized_pnl: float
    bonus: float

class PositionInfo(NamedTuple):
    symbol: str
    position_side: str # LONG or SHORT
    unrealized_pnl: float
    entry_price: float
    position_amt: float # Position amount
    initial_margin: float
    leverage: int
    margin_type: str # CROSS or ISOLATED
    # Add other relevant fields from API response as needed
    # e.g., markPrice, liquidationPrice, etc.
    # For now, keeping it concise based on common needs.
    position_id: Optional[int] = None # Example: some APIs return a position ID
    
class BitUnixClient:
    BASE_URL = "https://fapi.bitunix.com" # Updated Base URL for futures API

    def __init__(self):
        self.api_key = os.getenv("BITUNIX_API_KEY")
        self.secret_key = os.getenv("BITUNIX_SECRET_KEY")
        
        self.public_only = False
        if not self.api_key or not self.secret_key:
            print("Warning: API key or secret key not set. Only public endpoints (like klines) will work.")
            self.public_only = True

    def _sha256_hex(self, input_string: str) -> str:
        return hashlib.sha256(input_string.encode('utf-8')).hexdigest()

    def _generate_signature(self, nonce: str, timestamp: str, method: str, endpoint: str, query_params_str: str, body_str: str) -> str:
        if self.public_only or not self.api_key or not self.secret_key:
            # Should not be called for public endpoints or if keys are missing
            return "" 

        # Signature steps from Bitunix documentation:
        # 1. queryParams (already constructed as query_params_str)
        # 2. body (already constructed as body_str)
        # 3. Signature calculation
        #    String digest = SHA256(nonce + timestamp + api-key + queryParams + body)
        #    String sign = SHA256(digest + secretKey)

        digest_input = nonce + timestamp + self.api_key + query_params_str + body_str
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Digest Input: '{digest_input}'")
        
        digest = self._sha256_hex(digest_input)
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Digest Output: '{digest}'")

        sign_input = digest + self.secret_key
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Sign Input (digest + secretKey): '{digest} + YOUR_SECRET_KEY'") # Don't log full secret
        
        sign = self._sha256_hex(sign_input)
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Final Sign Output: '{sign}'")
        return sign

    def _get_auth_headers(self, nonce: str, timestamp: str, signature: str) -> Dict[str, str]:
        if self.public_only or not self.api_key:
            return {"Content-Type": "application/json"}
            
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": signature,
        }

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, is_private: bool = False) -> Any:
        url = f"{self.BASE_URL}{endpoint}"
        
        query_params_str = ""
        if params:
            # Sort query parameters by key in ascending ASCII order
            # Concatenate them: key1value1key2value2...
            # Example: {"id": 1, "uid": 200} becomes "id1uid200"
            # This interpretation of "id1uid200" is based on the doc's example.
            # A more standard way is "id=1&uid=200". If this fails, the format needs re-evaluation.
            sorted_params = sorted(params.items())
            query_params_str = "".join([f"{k}{v}" for k, v in sorted_params])
            if DEBUG_SIGNATURE and is_private:
                print(f"[DEBUG Signature] Sorted Query Params String: '{query_params_str}'")
        
        body_str = ""
        if data and (method == "POST" or method == "PUT"):
            # For POST/PUT, body is JSON string without spaces, as per docs.
            body_str = json.dumps(data, separators=(',', ':'), sort_keys=True) # Sort keys for consistent body string
            if DEBUG_SIGNATURE and is_private:
                print(f"[DEBUG Signature] Body String for signing: '{body_str}'")
        elif method == "GET" and data is not None:
             if DEBUG_SIGNATURE:
                print(f"[DEBUG Signature] Warning: Data provided for GET request, will be ignored in signing body_str. Data: {data}")

        headers: Dict[str, str]
        if is_private:
            if self.public_only:
                raise ValueError("Cannot call private endpoint without API key and secret.")
            
            nonce = str(uuid.uuid4()).replace("-", "") # 32-char random string
            timestamp_ms = str(int(time.time() * 1000))
            
            signature = self._generate_signature(nonce, timestamp_ms, method, endpoint, query_params_str, body_str)
            headers = self._get_auth_headers(nonce, timestamp_ms, signature)
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Request] Auth Headers for {method} {url}: {headers}")
        else:
            headers = {"Content-Type": "application/json"}
            if self.api_key: # Some public endpoints might still benefit from or expect an API key
                 headers["api-key"] = self.api_key # Using 'api-key' as per private header spec
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Request] Public Headers for {method} {url}: {headers}")

        # For GET requests, params are in URL, data should be None.
        # For POST/PUT, data is the JSON body, params should generally be None (or handled if API uses both).
        actual_data_for_request = body_str if data is not None and (method == "POST" or method == "PUT") else None
        actual_params_for_request = params if method == "GET" or (method != "GET" and params) else None # Allow params for non-GET if API needs it

        if DEBUG_SIGNATURE:
            print(f"[DEBUG Request] Making {method} request to: {url}")
            print(f"[DEBUG Request] URL Params: {actual_params_for_request}")
            print(f"[DEBUG Request] Request Body: {actual_data_for_request}")

        try:
            response = requests.request(method, url, params=actual_params_for_request, data=actual_data_for_request, headers=headers)
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Response] Status Code: {response.status_code}")
                print(f"[DEBUG Response] Headers: {response.headers}")
                try:
                    print(f"[DEBUG Response] Text: {response.text[:500]}...") # Print first 500 chars
                except Exception:
                    print("[DEBUG Response] Could not print response text.")

            response.raise_for_status()
            response_data = response.json()
            if response_data.get("code") == 0:
                return response_data.get("data")
            else:
                error_message = response_data.get("msg", "Unknown API error")
                print(f"API error for {method} {url}: {error_message} (Code: {response_data.get('code')}) - Response: {response.text}")
                raise requests.exceptions.HTTPError(f"API Error: {error_message} (Code: {response_data.get('code')})", response=response)

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {http_err.response.text if http_err.response else 'No response text'}") 
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            raise
        except json.JSONDecodeError as json_err:
            print(f"JSON decode error for {method} {url}: {json_err}. Response text: {response.text if 'response' in locals() else 'Response object not available'}")
            raise

    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None, # Unix timestamp in ms
        end_time: Optional[int] = None,   # Unix timestamp in ms
        limit: Optional[int] = None,      # Default 100, max 200
        kline_type: Optional[str] = None  # LAST_PRICE or MARK_PRICE
    ) -> List[Candlestick]:
        """Fetches historical kline (candlestick) data."""
        endpoint = "/api/v1/futures/market/kline"
        params_dict = {"symbol": symbol, "interval": interval}
        if start_time is not None: params_dict["startTime"] = start_time
        if end_time is not None: params_dict["endTime"] = end_time
        if limit is not None: params_dict["limit"] = limit
        if kline_type is not None: params_dict["type"] = kline_type
        raw_klines = self._request("GET", endpoint, params=params_dict, is_private=False)
        
        candlesticks = []
        if raw_klines: # Ensure raw_klines is not None and is iterable
            for k in raw_klines:
                # Response fields: open, high, low, close, time, quoteVol, baseVol, type
                # Note: API docs show 'quoteVol' twice. Assuming first is quote, second is base as per common patterns.
                # 'time' is the start time of the kline.
                candlesticks.append(
                    Candlestick(
                        open_time=int(k["time"]),
                        open_price=float(k["open"]),
                        high_price=float(k["high"]),
                        low_price=float(k["low"]),
                        close_price=float(k["close"]),
                        # API docs are ambiguous on quoteVol vs baseVol. Assuming baseVol is 'volume' and quoteVol is 'quote_volume'
                        # Adjust if API behaves differently.
                        volume=float(k.get("baseVol", 0.0)), # Use .get for safety if fields are missing
                        quote_volume=float(k.get("quoteVol", 0.0)),
                        kline_type=k.get("type")
                    )
                )
        return candlesticks

    def get_account_balance(self, margin_coin: str) -> List[AccountBalance]:
        """Fetches account balance for a specific margin coin."""
        if self.public_only:
            print("Cannot fetch account balance without API key/secret.")
            return []
        endpoint = "/api/v1/futures/account"
        params = {"marginCoin": margin_coin}
        
        # The API returns the account object directly in the "data" field, not a list.
        account_data_dict = self._request("GET", endpoint, params=params, is_private=True)
        
        balances = []
        if account_data_dict and isinstance(account_data_dict, dict):
            # Ensure all required keys are present before creating the AccountBalance object
            # This provides more robust error handling if the API response structure changes slightly.
            required_keys = ["marginCoin", "available", "frozen", "margin", "transfer", 
                             "positionMode", "crossUnrealizedPNL", "isolationUnrealizedPNL"]
            if all(key in account_data_dict for key in required_keys):
                balances.append(AccountBalance(
                    margin_coin=str(account_data_dict["marginCoin"]),
                    available=float(account_data_dict["available"]),
                    frozen=float(account_data_dict["frozen"]),
                    margin=float(account_data_dict["margin"]),
                    transfer=float(account_data_dict["transfer"]),
                    position_mode=str(account_data_dict["positionMode"]),
                    cross_unrealized_pnl=float(account_data_dict["crossUnrealizedPNL"]),
                    isolation_unrealized_pnl=float(account_data_dict["isolationUnrealizedPNL"]),
                    bonus=float(account_data_dict.get("bonus", 0.0)) # bonus is optional
                ))
            else:
                missing_keys = [key for key in required_keys if key not in account_data_dict]
                print(f"[DEBUG Balance] API response for account balance is missing keys: {missing_keys}. Response: {account_data_dict}")
        elif account_data_dict: # If not None and not a dict (which would be unexpected now)
             print(f"[DEBUG Balance] Expected dict for account_data_dict, got {type(account_data_dict)}: {account_data_dict}")
        return balances

    def get_open_positions(self, symbol: Optional[str] = None, margin_coin: Optional[str] = None) -> List[PositionInfo]:
        """Fetches current open positions."""
        if self.public_only:
            print("Cannot fetch open positions without API key/secret.")
            return []

        endpoint = "/api/v1/futures/position/pending"
        params = {}
        if symbol:
            params["symbol"] = symbol
        if margin_coin:
            params["marginCoin"] = margin_coin
            
        raw_positions = self._request("GET", endpoint, params=params if params else None, is_private=True)
        
        positions = []
        if raw_positions and isinstance(raw_positions, list):
            for p_item in raw_positions:
                if not isinstance(p_item, dict):
                    print(f"[DEBUG Position] Expected dict item in position list, got {type(p_item)}: {p_item}")
                    continue
                # Add checks for required keys in p_item as done for account_balance for robustness
                required_pos_keys = ["symbol", "positionSide", "unrealizedPNL", "entryPrice", 
                                     "positionAmt", "initialMargin", "leverage", "marginType"]
                if all(key in p_item for key in required_pos_keys):
                    positions.append(PositionInfo(
                        symbol=str(p_item["symbol"]),
                        position_side=str(p_item["positionSide"]),
                        unrealized_pnl=float(p_item["unrealizedPNL"]),
                        entry_price=float(p_item["entryPrice"]),
                        position_amt=float(p_item["positionAmt"]),
                        initial_margin=float(p_item["initialMargin"]),
                        leverage=int(p_item["leverage"]),
                        margin_type=str(p_item["marginType"]),
                        position_id=p_item.get("positionId") # positionId might be optional or not present
                    ))
                else:
                    missing_keys = [key for key in required_pos_keys if key not in p_item]
                    print(f"[DEBUG Position] API response for a position is missing keys: {missing_keys}. Item: {p_item}")
        elif raw_positions:
             print(f"[DEBUG Position] Expected list for raw_positions, got {type(raw_positions)}: {raw_positions}")
        return positions

    # Remove placeholder example methods
    # def get_example_endpoint(self, params=None):
    #     return self._request("GET", "/v1/example-data", params=params)

    # def post_example_endpoint(self, data=None):
    #     return self._request("POST", "/v1/example-action", data=data) 