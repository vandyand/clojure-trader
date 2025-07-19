#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("check_positions")

# Check if oandapyV20 is installed
try:
    from oandapyV20 import API
    from oandapyV20.endpoints.positions import OpenPositions
    from oandapyV20.endpoints.accounts import AccountDetails
    OANDA_AVAILABLE = True
except ImportError:
    logger.error("oandapyV20 not installed. Run: pip install oandapyV20")
    OANDA_AVAILABLE = False
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Check current OANDA positions")
    parser.add_argument("--account-id", type=str, help="OANDA account ID (overrides env var)")
    parser.add_argument("--api-token", type=str, help="OANDA API token (overrides env var)")
    return parser.parse_args()

def get_account_info(api, account_id):
    """Get account information including balance and NAV"""
    try:
        request = AccountDetails(accountID=account_id)
        response = api.request(request)
        account = response.get('account', {})
        
        return {
            'balance': float(account.get('balance', 0)),
            'nav': float(account.get('NAV', 0)),
            'currency': account.get('currency', 'Unknown'),
            'margin_used': float(account.get('marginUsed', 0)),
            'margin_available': float(account.get('marginAvailable', 0)),
            'position_value': float(account.get('positionValue', 0)),
            'pl': float(account.get('pl', 0)),
            'unrealized_pl': float(account.get('unrealizedPL', 0))
        }
    except Exception as e:
        logger.error(f"Error getting account details: {e}")
        return {}

def get_current_positions(api, account_id):
    """Get detailed information on current positions"""
    try:
        request = OpenPositions(accountID=account_id)
        response = api.request(request)
        positions = response.get("positions", [])
        
        formatted_positions = []
        for position in positions:
            instrument = position.get("instrument")
            
            # Get long position details
            long_units = int(position.get("long", {}).get("units", "0"))
            long_pl = float(position.get("long", {}).get("unrealizedPL", "0"))
            long_avg_price = position.get("long", {}).get("averagePrice")
            
            # Get short position details
            short_units = int(position.get("short", {}).get("units", "0"))
            short_pl = float(position.get("short", {}).get("unrealizedPL", "0"))
            short_avg_price = position.get("short", {}).get("averagePrice")
            
            # Net position
            net_units = long_units + short_units  # short_units will be negative
            
            if net_units != 0:
                pos_data = {
                    "instrument": instrument,
                    "units": net_units,
                    "direction": "LONG" if net_units > 0 else "SHORT",
                    "unrealized_pl": long_pl + short_pl,
                    "long_units": long_units,
                    "long_avg_price": long_avg_price,
                    "short_units": short_units,
                    "short_avg_price": short_avg_price
                }
                formatted_positions.append(pos_data)
        
        return formatted_positions
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []

def main():
    """Main function"""
    args = parse_args()
    
    # Get credentials
    account_id = args.account_id or os.environ.get('OANDA_DEMO_ACCOUNT_ID')
    api_token = args.api_token or os.environ.get('OANDA_DEMO_KEY')
    
    if not account_id:
        logger.error("No account ID provided. Please set OANDA_DEMO_ACCOUNT_ID environment variable or use --account-id")
        return 1
    
    if not api_token:
        logger.error("No API token provided. Please set OANDA_DEMO_KEY environment variable or use --api-token")
        return 1
    
    logger.info(f"Checking positions for account {account_id}")
    
    # Initialize API
    api = API(access_token=api_token, environment="practice")
    
    # Get account info
    account_info = get_account_info(api, account_id)
    logger.info(f"Account Info: {account_info}")
    
    # Get positions
    positions = get_current_positions(api, account_id)
    
    if not positions:
        logger.info("No positions found")
        return 0
    
    # Print positions in a table format
    print("\nCurrent Positions:")
    print("-" * 100)
    print(f"{'Instrument':<10} | {'Direction':<8} | {'Units':<10} | {'Unrealized P/L':<15} | {'Long Units':<10} | {'Long Price':<10} | {'Short Units':<10} | {'Short Price':<10}")
    print("-" * 100)
    
    for pos in positions:
        print(f"{pos['instrument']:<10} | {pos['direction']:<8} | {pos['units']:<10} | {pos['unrealized_pl']:<15.2f} | {pos['long_units']:<10} | {pos['long_avg_price'] or 'N/A':<10} | {pos['short_units']:<10} | {pos['short_avg_price'] or 'N/A':<10}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 