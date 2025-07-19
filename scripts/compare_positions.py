#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).resolve().parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("compare_positions")

# Import oandapyV20
try:
    from oandapyV20 import API
    from oandapyV20.endpoints.positions import OpenPositions
    from oandapyV20.endpoints.accounts import AccountDetails
    from oandapyV20.endpoints.pricing import PricingInfo
    OANDA_AVAILABLE = True
except ImportError:
    logger.error("oandapyV20 not installed. Run: pip install oandapyV20")
    OANDA_AVAILABLE = False
    sys.exit(1)

# Import position sizing module
try:
    from trading_systems.rl.position_sizing import get_target_position_amount, get_latest_price, is_forex
except ImportError:
    try:
        sys.path.append(str(Path(__file__).resolve().parent.parent / "trading_systems" / "rl")))
        from position_sizing import get_target_position_amount, get_latest_price, is_forex
    except ImportError:
        logger.error("Could not import position_sizing module. Make sure the path is correct.")
        sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Compare OANDA positions with expected positions")
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

def get_position_size_in_usd(instrument, units, api, account_id):
    """Calculate position size in USD based on current pricing"""
    # Get the current price
    latest_price = get_latest_price(instrument, api, account_id)
    if not latest_price:
        logger.warning(f"Could not get price for {instrument}, skipping USD calculation")
        return 0
    
    # Calculate USD amount using the same logic as in position_sizing.py but in reverse
    abs_units = abs(units)
    
    # Try to calculate USD value based on instrument characteristics
    usd_position_size = 0
    try:
        # For USD as base currency (USD_JPY, USD_CAD, etc.)
        if instrument.startswith("USD_"):
            if instrument.endswith("JPY"):
                usd_position_size = abs_units / (latest_price * 0.01)
            else:
                usd_position_size = abs_units / latest_price
        # For USD as quote currency (EUR_USD, GBP_USD, etc.)
        elif instrument.endswith("USD"):
            usd_position_size = abs_units * latest_price
        # For JPY crosses
        elif instrument.endswith("JPY"):
            usd_jpy_price = get_latest_price("USD_JPY", api, account_id)
            if usd_jpy_price:
                usd_position_size = (abs_units * latest_price) / usd_jpy_price
        # For CAD crosses
        elif instrument.endswith("CAD"):
            usd_cad_price = get_latest_price("USD_CAD", api, account_id)
            if usd_cad_price:
                usd_position_size = (abs_units * latest_price) / usd_cad_price
        # For CHF crosses
        elif instrument.endswith("CHF"):
            usd_chf_price = get_latest_price("USD_CHF", api, account_id)
            if usd_chf_price:
                usd_position_size = (abs_units * latest_price) / usd_chf_price
        # For GBP crosses
        elif instrument.endswith("GBP"):
            gbp_usd_price = get_latest_price("GBP_USD", api, account_id)
            if gbp_usd_price:
                usd_position_size = abs_units * latest_price / gbp_usd_price
        # For AUD crosses
        elif instrument.endswith("AUD"):
            aud_usd_price = get_latest_price("AUD_USD", api, account_id)
            if aud_usd_price:
                usd_position_size = abs_units * latest_price / aud_usd_price
        # For NZD crosses
        elif instrument.endswith("NZD"):
            nzd_usd_price = get_latest_price("NZD_USD", api, account_id)
            if nzd_usd_price:
                usd_position_size = abs_units * latest_price / nzd_usd_price
        
        return usd_position_size
    except Exception as e:
        logger.error(f"Error calculating USD position size for {instrument}: {e}")
        return 0

def get_expected_positions():
    """Get expected positions from sync_positions.py hardcoded values"""
    # Position sizes from the logs
    positions_data = [
        {"instrument": "EUR_USD", "direction": "SHORT", "position_size": 6.896073, "usd_amount": 0.31},
        {"instrument": "USD_JPY", "direction": "LONG", "position_size": 15.530363, "usd_amount": 0.43},
        {"instrument": "GBP_USD", "direction": "SHORT", "position_size": 31.892446, "usd_amount": 1.69},
        {"instrument": "AUD_USD", "direction": "SHORT", "position_size": 5.810788, "usd_amount": 0.15},
        {"instrument": "USD_CHF", "direction": "SHORT", "position_size": 161.129704, "usd_amount": 7.70},
        {"instrument": "USD_CAD", "direction": "SHORT", "position_size": 164.208389, "usd_amount": 4.70},
        {"instrument": "NZD_USD", "direction": "LONG", "position_size": 31.659876, "usd_amount": 0.75},
        {"instrument": "EUR_JPY", "direction": "SHORT", "position_size": 46.723941, "usd_amount": 1.67},
        {"instrument": "GBP_JPY", "direction": "SHORT", "position_size": 83.755735, "usd_amount": 2.52},
        {"instrument": "EUR_GBP", "direction": "LONG", "position_size": 69.947045, "usd_amount": 2.50},
        {"instrument": "EUR_CHF", "direction": "LONG", "position_size": 84.886707, "usd_amount": 3.03},
        {"instrument": "EUR_AUD", "direction": "LONG", "position_size": 10.932068, "usd_amount": 0.39},
        {"instrument": "EUR_CAD", "direction": "LONG", "position_size": 44.346064, "usd_amount": 1.58},
        {"instrument": "GBP_CHF", "direction": "SHORT", "position_size": 192.469962, "usd_amount": 5.79},
        {"instrument": "AUD_JPY", "direction": "SHORT", "position_size": 35.148946, "usd_amount": 2.19},
        {"instrument": "AUD_CHF", "direction": "SHORT", "position_size": 98.043865, "usd_amount": 6.11},
        {"instrument": "CAD_JPY", "direction": "LONG", "position_size": 62.559518, "usd_amount": 3.50},
        {"instrument": "NZD_JPY", "direction": "SHORT", "position_size": 13.615224, "usd_amount": 0.92},
        {"instrument": "GBP_AUD", "direction": "SHORT", "position_size": 51.943106, "usd_amount": 1.56},
        {"instrument": "AUD_NZD", "direction": "LONG", "position_size": 40.172846, "usd_amount": 2.50}
    ]
    
    # Simply round position_size to get target units
    expected_positions = []
    for pos in positions_data:
        instrument = pos["instrument"]
        position_size = pos["position_size"]
        direction = pos["direction"]
        
        # Round to nearest integer
        target_units = round(position_size)
        
        if direction == "SHORT":
            target_units = -target_units
        
        expected_pos = {
            "instrument": instrument,
            "direction": direction,
            "position_size": position_size,
            "units": target_units,
            "usd_amount": pos["usd_amount"]
        }
        expected_positions.append(expected_pos)
    
    return expected_positions

def compare_positions(current_positions, expected_positions):
    """Compare current and expected positions"""
    # Build maps for easier comparison
    current_map = {pos["instrument"]: pos for pos in current_positions}
    expected_map = {pos["instrument"]: pos for pos in expected_positions}
    
    # All instruments in either list
    all_instruments = set(current_map.keys()) | set(expected_map.keys())
    
    comparison_results = []
    for instrument in sorted(all_instruments):
        current = current_map.get(instrument, {"units": 0, "direction": "NONE"})
        expected = expected_map.get(instrument, {"units": 0, "direction": "NONE"})
        
        # Calculate differences
        current_units = current.get("units", 0)
        expected_units = expected.get("units", 0) if expected.get("units") is not None else 0
        
        # Fix direction for comparison
        if current_units == 0:
            current_direction = "NONE"
        else:
            current_direction = "LONG" if current_units > 0 else "SHORT"
            
        if expected_units == 0:
            expected_direction = "NONE"
        else:
            expected_direction = expected.get("direction", "LONG" if expected_units > 0 else "SHORT")
        
        # Check if directions match
        direction_match = current_direction == expected_direction
        units_match = abs(current_units) == abs(expected_units)
        
        comparison_results.append({
            "instrument": instrument,
            "current_direction": current_direction,
            "current_units": current_units,
            "expected_direction": expected_direction,
            "expected_units": expected_units,
            "direction_match": direction_match,
            "units_match": units_match
        })
    
    return comparison_results

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
    
    logger.info(f"Comparing positions for account {account_id}")
    
    # Initialize API
    api = API(access_token=api_token, environment="practice")
    
    # Get account info
    account_info = get_account_info(api, account_id)
    logger.info(f"Account Info: Balance=${account_info['balance']}, NAV=${account_info['nav']}")
    
    # Get current positions
    current_positions = get_current_positions(api, account_id)
    
    if not current_positions:
        logger.info("No positions found in the account")
        return 0
    
    # Get expected positions
    expected_positions = get_expected_positions()
    
    # Calculate USD values for current positions
    for pos in current_positions:
        usd_value = get_position_size_in_usd(pos["instrument"], pos["units"], api, account_id)
        pos["usd_value"] = usd_value
    
    # Compare positions
    comparison = compare_positions(current_positions, expected_positions)
    
    # Print results
    print("\nCurrent Account Positions:")
    print("-" * 90)
    print(f"{'Instrument':<10} | {'Direction':<8} | {'Units':<10} | {'USD Value':<15} | {'P/L':<10}")
    print("-" * 90)
    
    for pos in current_positions:
        print(f"{pos['instrument']:<10} | {pos['direction']:<8} | {pos['units']:<10} | ${pos.get('usd_value', 0):<14.2f} | ${pos['unrealized_pl']:<9.2f}")
    
    print("\nPosition Comparison:")
    print("-" * 120)
    print(f"{'Instrument':<10} | {'Current Dir':<10} | {'Current Units':<15} | {'Expected Dir':<12} | {'Expected Units':<15} | {'Dir Match':<10} | {'Units Match':<10}")
    print("-" * 120)
    
    for comp in comparison:
        print(f"{comp['instrument']:<10} | {comp['current_direction']:<10} | {comp['current_units']:<15} | {comp['expected_direction']:<12} | {comp['expected_units']:<15} | {'✓' if comp['direction_match'] else '✗':<10} | {'✓' if comp['units_match'] else '✗':<10}")
    
    # Summary
    matches = [c for c in comparison if c["direction_match"] and c["units_match"]]
    dir_mismatches = [c for c in comparison if not c["direction_match"]]
    unit_mismatches = [c for c in comparison if c["direction_match"] and not c["units_match"]]
    
    print(f"\nSummary: {len(matches)} matches, {len(dir_mismatches)} direction mismatches, {len(unit_mismatches)} unit mismatches")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 