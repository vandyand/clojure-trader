#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).resolve().parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_position_logic")

# Import position sizing module
try:
    from rl.position_sizing import get_latest_price, is_forex
except ImportError:
    logger.error("Could not import position_sizing module")
    sys.exit(1)

# Import OANDA trader if available
try:
    from rl.oanda_trader import OandaTrader
    OANDA_AVAILABLE = True
except ImportError:
    logger.warning("OandaTrader not available, will use mock data")
    OANDA_AVAILABLE = False

def calculate_usd_value(instrument, units, latest_price, api=None, account_id=None):
    """Calculate USD value based on instrument and units"""
    try:
        # For USD as base currency (USD_JPY, USD_CAD, etc.)
        if instrument.startswith("USD_"):
            if instrument.endswith("JPY"):
                return units / (latest_price * 0.01)
            else:
                return units / latest_price
        # For USD as quote currency (EUR_USD, GBP_USD, etc.)
        elif instrument.endswith("USD"):
            return units * latest_price
        # For crosses, we'd need additional price lookups
        # Using simplified approach for test
        else:
            return units
    except Exception as e:
        logger.error(f"Error calculating USD value for {instrument}: {e}")
        return 0

def calculate_units_for_usd_amount(instrument, usd_amount, latest_price, api=None, account_id=None):
    """Calculate units needed to achieve a target USD amount"""
    try:
        # For USD as base currency (USD_JPY, USD_CAD, etc.)
        if instrument.startswith("USD_"):
            if instrument.endswith("JPY"):
                return round(usd_amount * (latest_price * 0.01))
            else:
                return round(usd_amount * latest_price)
        # For USD as quote currency (EUR_USD, GBP_USD, etc.)
        elif instrument.endswith("USD"):
            return round(usd_amount / latest_price)
        # For crosses, would need additional lookups
        else:
            # Just use a placeholder approach for now
            return round(usd_amount)
    except Exception as e:
        logger.error(f"Error calculating units for USD amount for {instrument}: {e}")
        return 0

def test_position_sizing():
    """Test position sizing logic with direct USD-based approach"""
    
    # Sample positions from sync_positions.py
    positions = [
        {"instrument": "EUR_USD", "direction": "SHORT", "position_size": 6.896073, "usd_amount": 0.31},
        {"instrument": "USD_JPY", "direction": "LONG", "position_size": 15.530363, "usd_amount": 0.43},
        {"instrument": "GBP_USD", "direction": "SHORT", "position_size": 31.892446, "usd_amount": 1.69},
        {"instrument": "AUD_USD", "direction": "SHORT", "position_size": 5.810788, "usd_amount": 0.15},
        {"instrument": "USD_CHF", "direction": "SHORT", "position_size": 161.129704, "usd_amount": 7.70},
        {"instrument": "USD_CAD", "direction": "SHORT", "position_size": 164.208389, "usd_amount": 4.70},
        {"instrument": "NZD_USD", "direction": "LONG", "position_size": 31.659876, "usd_amount": 0.75}
    ]
    
    # Initialize API if available
    api = None
    account_id = None
    
    if OANDA_AVAILABLE:
        try:
            account_id = os.environ.get('OANDA_DEMO_ACCOUNT_ID')
            access_token = os.environ.get('OANDA_DEMO_KEY')
            
            if not account_id or not access_token:
                logger.warning("OANDA credentials not set, using mock prices")
            else:
                trader = OandaTrader(account_id=account_id, access_token=access_token)
                api = trader.api
                logger.info(f"Connected to OANDA account {account_id}")
        except Exception as e:
            logger.error(f"Error connecting to OANDA: {e}")
    
    # Calculate target units and validate USD values
    results = []
    
    print("\nPosition Sizing Test Results (Direct USD-Based):")
    print("-" * 100)
    print(f"{'Instrument':<10} | {'Direction':<8} | {'Position Size':<15} | {'USD Amount':<12} | {'Target Units':<15} | {'Calc USD':<12}")
    print("-" * 100)
    
    for pos in positions:
        instrument = pos["instrument"]
        direction = pos["direction"]
        position_size = pos["position_size"]
        target_usd = pos["usd_amount"]
        
        # Get latest price
        latest_price = None
        if api and account_id:
            latest_price = get_latest_price(instrument, api, account_id)
        
        # If no API or price not available, use mock price
        if not latest_price:
            # Mock prices for demonstration
            mock_prices = {
                "EUR_USD": 1.05,
                "USD_JPY": 155.0, 
                "GBP_USD": 1.25,
                "AUD_USD": 0.65,
                "USD_CHF": 0.92,
                "USD_CAD": 1.37,
                "NZD_USD": 0.60
            }
            latest_price = mock_prices.get(instrument, 1.0)
        
        # Calculate target units directly from USD amount
        target_units = calculate_units_for_usd_amount(instrument, target_usd, latest_price, api, account_id)
        if direction == "SHORT":
            target_units = -abs(target_units)
        else:
            target_units = abs(target_units)
        
        # Verify by calculating USD value of these units
        usd_value = calculate_usd_value(instrument, abs(target_units), latest_price, api, account_id)
        
        print(f"{instrument:<10} | {direction:<8} | {position_size:<15.6f} | ${target_usd:<11.2f} | {target_units:<15} | ${usd_value:<11.2f}")
        
        results.append({
            "instrument": instrument,
            "direction": direction,
            "position_size": position_size,
            "target_units": target_units,
            "target_usd": target_usd,
            "calculated_usd": usd_value,
            "latest_price": latest_price
        })
    
    print("-" * 100)
    
    # Show summary of differences
    print("\nUSD Value Comparison:")
    print("-" * 70)
    print(f"{'Instrument':<10} | {'Target USD':<12} | {'Calc USD':<12} | {'Diff':<12} | {'Diff %':<12}")
    print("-" * 70)
    
    for result in results:
        target_usd = result["target_usd"]
        calc_usd = result["calculated_usd"]
        diff = calc_usd - target_usd
        diff_pct = (diff / target_usd) * 100 if target_usd != 0 else 0
        
        print(f"{result['instrument']:<10} | ${target_usd:<11.2f} | ${calc_usd:<11.2f} | ${diff:<11.2f} | {diff_pct:<11.2f}%")
    
    print("-" * 70)

if __name__ == "__main__":
    test_position_sizing() 