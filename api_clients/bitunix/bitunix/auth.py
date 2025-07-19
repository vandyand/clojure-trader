"""
Authentication module for Bitunix API.
"""
import hashlib
import time
import uuid
from typing import Dict, Any, Optional
import json


DEBUG_SIGNATURE = False  # Set to True to enable verbose signature logging


class BitunixAuth:
    """Handles authentication and signature generation for Bitunix API."""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
    
    def _sha256_hex(self, input_string: str) -> str:
        """Generate SHA256 hash of the input string."""
        return hashlib.sha256(input_string.encode('utf-8')).hexdigest()
    
    def generate_signature(
        self,
        nonce: str,
        timestamp: str,
        method: str,
        endpoint: str,
        query_params_str: str,
        body_str: str
    ) -> str:
        """
        Generate signature for Bitunix API request.
        
        Signature steps from Bitunix documentation:
        1. queryParams (already constructed as query_params_str)
        2. body (already constructed as body_str)
        3. Signature calculation
           String digest = SHA256(nonce + timestamp + api-key + queryParams + body)
           String sign = SHA256(digest + secretKey)
        """
        digest_input = nonce + timestamp + self.api_key + query_params_str + body_str
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Digest Input: '{digest_input}'")
        
        digest = self._sha256_hex(digest_input)
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Digest Output: '{digest}'")
        
        sign_input = digest + self.secret_key
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Sign Input (digest + secretKey): '{digest} + YOUR_SECRET_KEY'")
        
        sign = self._sha256_hex(sign_input)
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Signature] Final Sign Output: '{sign}'")
        
        return sign
    
    def get_auth_headers(self, nonce: str, timestamp: str, signature: str) -> Dict[str, str]:
        """Get authentication headers for private endpoints."""
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": signature,
        }
    
    def prepare_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str, Dict[str, str]]:
        """
        Prepare authenticated request.
        
        Returns:
            tuple: (query_params_str, body_str, headers)
        """
        # Prepare query parameters string
        query_params_str = ""
        if params:
            # Sort query parameters by key in ascending ASCII order
            # Concatenate them: key1value1key2value2...
            sorted_params = sorted(params.items())
            query_params_str = "".join([f"{k}{v}" for k, v in sorted_params])
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Signature] Sorted Query Params String: '{query_params_str}'")
        
        # Prepare body string
        body_str = ""
        if data and (method == "POST" or method == "PUT"):
            # For POST/PUT, body is JSON string without spaces
            body_str = json.dumps(data, separators=(',', ':'), sort_keys=True)
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Signature] Body String for signing: '{body_str}'")
        
        # Generate authentication values
        nonce = str(uuid.uuid4()).replace("-", "")  # 32-char random string
        timestamp_ms = str(int(time.time() * 1000))
        
        # Generate signature
        signature = self.generate_signature(
            nonce, timestamp_ms, method, endpoint, query_params_str, body_str
        )
        
        # Get headers
        headers = self.get_auth_headers(nonce, timestamp_ms, signature)
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Request] Auth Headers: {headers}")
        
        return query_params_str, body_str, headers
