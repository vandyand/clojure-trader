"""
Debug script to inspect raw account API response.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitunix.client import BitUnixClient
import json

def main():
    print("Fetching raw account data to inspect available fields...")
    
    client = BitUnixClient()
    
    if client.public_only:
        print("ERROR: API keys not configured.")
        return
    
    # Temporarily enable debug mode
    from bitunix import auth
    auth.DEBUG_SIGNATURE = True
    
    try:
        # Get raw response by calling the internal _request method
        endpoint = "/api/v1/futures/account"
        params = {"marginCoin": "USDT"}
        
        raw_data = client._request("GET", endpoint, params=params, is_private=True)
        
        print("\n" + "="*60)
        print("RAW ACCOUNT API RESPONSE:")
        print("="*60)
        print(json.dumps(raw_data, indent=2))
        print("="*60)
        
        # Check if there are fields we're not capturing
        if isinstance(raw_data, dict):
            print("\nAvailable fields in account data:")
            for key, value in raw_data.items():
                print(f"  - {key}: {type(value).__name__} = {value}")
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    main() 