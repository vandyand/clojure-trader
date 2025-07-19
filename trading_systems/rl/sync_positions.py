#!/usr/bin/env python3
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sync_positions")

# Check if oandapyV20 is installed
try:
    import oandapyV20
    OANDA_AVAILABLE = True
except ImportError:
    logger.error("oandapyV20 not installed. Run: pip install oandapyV20")
    OANDA_AVAILABLE = False

# Import our position sizing module
try:
    from rl.position_sizing import get_target_position_amount, get_latest_price, is_forex
except ImportError:
    logger.error("Failed to import position_sizing module.")
    sys.exit(1)

# Import our OANDA trader
try:
    from rl.oanda_trader import OandaTrader
except ImportError:
    logger.error("Failed to import OandaTrader. Make sure oanda_trader.py is in the rl directory.")
    sys.exit(1)

def parse_terminal_log_positions(log_content=None):
    """
    Parse positions from a terminal log
    
    Args:
        log_content: String containing terminal log output
        
    Returns:
        Dictionary of positions
    """
    # If no log content provided, use hardcoded positions from attached snippet
    if not log_content:
        # Positions from the manually added selection
        positions = [
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
        
        result = {
            "account_size": 1000.0,
            "risk_amount": 50.0,
            "positions": positions
        }
        return result
    
    # Parse log content if provided
    # This would parse a terminal log format like the one shown in the example
    # For now, just return hardcoded positions
    return parse_terminal_log_positions()

def save_positions_to_file(positions, filename=None):
    """
    Save positions to a JSON file
    
    Args:
        positions: Dictionary of positions
        filename: Optional filename, if None uses timestamp
        
    Returns:
        Path to saved file
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signals/manual_signals_{timestamp}.json"
    
    file_path = os.path.join(parent_dir, filename)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(positions, f, indent=2)
    
    logger.info(f"Saved positions to {file_path}")
    return file_path

def get_current_positions(trader):
    """
    Get current positions from OANDA
    
    Args:
        trader: OandaTrader instance
        
    Returns:
        Dictionary of current positions {instrument: units}
    """
    try:
        from oandapyV20.endpoints.positions import OpenPositions
        r = OpenPositions(accountID=trader.account_id)
        response = trader.api.request(r)
        positions = response.get("positions", [])
        
        current_positions = {}
        for position in positions:
            instrument = position.get("instrument")
            long_units = int(position.get("long", {}).get("units", "0"))
            short_units = int(position.get("short", {}).get("units", "0"))
            
            # Net position (positive for long, negative for short)
            net_units = long_units + short_units  # short_units will be negative
            
            if net_units != 0:
                current_positions[instrument] = net_units
                
        return current_positions
    except Exception as e:
        logger.error(f"Error getting current positions: {e}")
        return {}

def calculate_position_changes(current_positions, target_positions, api, account_id):
    """
    Calculate the changes needed to align current positions with target positions
    
    Args:
        current_positions: Dictionary of current positions {instrument: units}
        target_positions: List of target position dictionaries
        api: OANDA API client
        account_id: OANDA account ID
        
    Returns:
        List of position changes {instrument, units}
    """
    changes = []
    
    # Create a map of target positions for easy lookup
    target_position_map = {}
    for pos in target_positions:
        instrument = pos["instrument"]
        direction = pos["direction"]
        
        # Get actual units if provided in the position data
        if "units" in pos and pos["units"] is not None:
            target_units = int(pos["units"])
            if direction == "SHORT":
                target_units = -abs(target_units)
        # Simply round the position_size to get target units
        elif "position_size" in pos:
            position_size = float(pos["position_size"])
            
            # Round to nearest integer
            target_units = round(position_size)
            
            # Apply direction
            if direction == "SHORT":
                target_units = -abs(target_units)
            else:  # LONG
                target_units = abs(target_units)
                
            logger.info(f"Target position for {instrument}: {direction} {abs(target_units)} units (rounded from position_size: {position_size})")
        else:
            logger.warning(f"No units or position_size specified for {instrument}, skipping")
            continue
            
        target_position_map[instrument] = target_units
    
    # Calculate changes for existing instruments
    for instrument, current_units in current_positions.items():
        target_units = target_position_map.get(instrument, 0)
        delta_units = target_units - current_units
        
        if delta_units != 0:
            changes.append({
                "instrument": instrument,
                "units": delta_units
            })
        
        # Remove from target map so we don't process it again
        if instrument in target_position_map:
            del target_position_map[instrument]
    
    # Add new positions for remaining targets
    for instrument, target_units in target_position_map.items():
        if target_units != 0:
            changes.append({
                "instrument": instrument,
                "units": target_units
            })
    
    return changes

def sync_positions(trader, target_positions):
    """
    Synchronize OANDA positions with target positions by calculating and executing only necessary changes
    
    Args:
        trader: OandaTrader instance
        target_positions: Dictionary with target positions
        
    Returns:
        True if successful, False otherwise
    """
    position_list = target_positions.get("positions", [])
    
    if not position_list:
        logger.warning("No target positions found")
        return False
    
    # Get current positions
    logger.info("Getting current positions from OANDA")
    current_positions = get_current_positions(trader)
    logger.info(f"Current positions: {current_positions}")
    
    # Calculate required changes
    changes = calculate_position_changes(current_positions, position_list, trader.api, trader.account_id)
    logger.info(f"Position changes to execute: {changes}")
    
    if not changes:
        logger.info("No position changes needed")
        return True
    
    # Execute changes
    success_count = 0
    fail_count = 0
    
    for change in changes:
        instrument = change["instrument"]
        units = change["units"]
        
        if units == 0:
            continue
            
        logger.info(f"Placing order for {instrument}: {'BUY' if units > 0 else 'SELL'} {abs(units)} units")
        order_id = trader.place_order(instrument, units)
        
        if order_id:
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"Executed {success_count} orders, {fail_count} failed")
    
    # Validate positions after changes
    if success_count > 0:
        logger.info("Validating positions USD values...")
        validate_position_usd_values(trader, position_list)
    
    return success_count > 0 or len(changes) == 0

def validate_position_usd_values(trader, target_positions):
    """
    Validate that actual position USD values match target USD values
    
    Args:
        trader: OandaTrader instance
        target_positions: List of target position dictionaries
    """
    # Wait a moment for positions to update
    time.sleep(2)
    
    # Get current positions
    current_positions = get_current_positions(trader)
    
    if not current_positions:
        logger.warning("No positions found for validation")
        return
    
    # Create a map of position data by instrument
    position_map = {}
    for instrument, units in current_positions.items():
        # Get latest price for USD calculation
        latest_price = get_latest_price(instrument, trader.api, trader.account_id)
        
        if not latest_price:
            logger.warning(f"Could not get price for {instrument}, skipping validation")
            continue
        
        # Calculate USD value
        abs_units = abs(units)
        usd_value = 0
        
        try:
            # For USD as base currency (USD_JPY, USD_CAD, etc.)
            if instrument.startswith("USD_"):
                if instrument.endswith("JPY"):
                    usd_value = abs_units / (latest_price * 0.01)
                else:
                    usd_value = abs_units / latest_price
            # For USD as quote currency (EUR_USD, GBP_USD, etc.)
            elif instrument.endswith("USD"):
                usd_value = abs_units * latest_price
            # For JPY crosses
            elif instrument.endswith("JPY"):
                usd_jpy_price = get_latest_price("USD_JPY", trader.api, trader.account_id)
                if usd_jpy_price:
                    usd_value = (abs_units * latest_price) / usd_jpy_price
            # For CAD crosses
            elif instrument.endswith("CAD"):
                usd_cad_price = get_latest_price("USD_CAD", trader.api, trader.account_id)
                if usd_cad_price:
                    usd_value = (abs_units * latest_price) / usd_cad_price
            # For CHF crosses
            elif instrument.endswith("CHF"):
                usd_chf_price = get_latest_price("USD_CHF", trader.api, trader.account_id)
                if usd_chf_price:
                    usd_value = (abs_units * latest_price) / usd_chf_price
            # For GBP crosses
            elif instrument.endswith("GBP"):
                gbp_usd_price = get_latest_price("GBP_USD", trader.api, trader.account_id)
                if gbp_usd_price:
                    usd_value = abs_units * latest_price * gbp_usd_price
            # For AUD crosses
            elif instrument.endswith("AUD"):
                aud_usd_price = get_latest_price("AUD_USD", trader.api, trader.account_id)
                if aud_usd_price:
                    usd_value = abs_units * latest_price * aud_usd_price
            # For NZD crosses
            elif instrument.endswith("NZD"):
                nzd_usd_price = get_latest_price("NZD_USD", trader.api, trader.account_id)
                if nzd_usd_price:
                    usd_value = abs_units * latest_price * nzd_usd_price
            else:
                logger.warning(f"Unsupported instrument type for USD calculation: {instrument}")
                usd_value = abs_units  # Fallback
        
            position_map[instrument] = {
                "units": units,
                "direction": "LONG" if units > 0 else "SHORT",
                "usd_value": usd_value
            }
        except Exception as e:
            logger.error(f"Error calculating USD value for {instrument}: {e}")
    
    # Compare with target positions
    logger.info("Position USD Value Validation:")
    logger.info("-" * 80)
    logger.info(f"{'Instrument':<10} | {'Direction':<8} | {'Actual Units':<12} | {'Target Size':<12} | {'Actual USD':<10} | {'Target USD':<10} | {'Match':<5}")
    logger.info("-" * 80)
    
    match_count = 0
    mismatch_count = 0
    
    for target in target_positions:
        instrument = target.get("instrument")
        target_direction = target.get("direction")
        target_size = target.get("position_size", 0)
        target_usd = target.get("usd_amount", 0)
        
        actual = position_map.get(instrument, {})
        actual_units = actual.get("units", 0)
        actual_direction = actual.get("direction", "NONE")
        actual_usd = actual.get("usd_value", 0)
        
        # Determine if values match (with some tolerance for USD)
        direction_match = target_direction == actual_direction
        units_match = abs(actual_units) == round(target_size)
        
        # Use a percentage or absolute tolerance depending on the USD amount
        if target_usd > 1.0:
            usd_match = abs(actual_usd - target_usd) < (target_usd * 0.20)  # 20% tolerance for larger amounts
        else:
            usd_match = abs(actual_usd - target_usd) < 0.25  # $0.25 tolerance for small amounts
        
        match_indicator = "✓" if usd_match else "✗"
        
        if usd_match:
            match_count += 1
        else:
            mismatch_count += 1
        
        logger.info(f"{instrument:<10} | {actual_direction:<8} | {actual_units:<12} | {target_size:<12.2f} | ${actual_usd:<9.2f} | ${target_usd:<9.2f} | {match_indicator}")
    
    logger.info("-" * 80)
    logger.info(f"Summary: {match_count} USD value matches, {mismatch_count} mismatches")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Sync OANDA positions with terminal log")
    
    parser.add_argument("--account-id", type=str, help="OANDA account ID (overrides env var)")
    parser.add_argument("--api-token", type=str, help="OANDA API token (overrides env var)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Don't actually place trades, just show what would be done")
    parser.add_argument("--verify-only", action="store_true",
                       help="Only verify account connection, don't sync positions")
    parser.add_argument("--show-reference", action="store_true",
                        help="Show reference table for USD-to-units conversion")
                       
    return parser.parse_args()

def show_reference_table(api=None, account_id=None):
    """
    Show a reference table for how USD amounts translate to units for different instruments
    
    Args:
        api: OANDA API client (optional)
        account_id: OANDA account ID (optional)
    """
    # Initialize API if needed
    if not api and OANDA_AVAILABLE:
        try:
            api_token = os.environ.get('OANDA_DEMO_KEY')
            if api_token:
                from oandapyV20 import API
                api = API(access_token=api_token, environment="practice")
                account_id = os.environ.get('OANDA_DEMO_ACCOUNT_ID')
        except Exception as e:
            logger.error(f"Error initializing API: {e}")
    
    # Example instruments
    instruments = [
        "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF", 
        "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP"
    ]
    
    # Example USD amounts
    usd_amounts = [0.10, 0.25, 0.50, 1.00, 2.00, 5.00, 10.00]
    
    # Print header
    print("\nReference Table: USD Amount to Units Conversion")
    print("=" * 100)
    header = f"{'Instrument':<10} | {'Price':<8} |"
    for amount in usd_amounts:
        header += f" ${amount:<6} |"
    print(header)
    print("-" * 100)
    
    # Calculate and print rows
    for instrument in instruments:
        latest_price = None
        if api and account_id:
            try:
                latest_price = get_latest_price(instrument, api, account_id)
            except Exception as e:
                logger.error(f"Error getting price for {instrument}: {e}")
        
        # Use mock price if API not available
        if not latest_price:
            mock_prices = {
                "EUR_USD": 1.05, "USD_JPY": 155.0, "GBP_USD": 1.25, 
                "AUD_USD": 0.65, "USD_CHF": 0.92, "USD_CAD": 1.37, 
                "NZD_USD": 0.60, "EUR_JPY": 165.0, "GBP_JPY": 190.0, 
                "EUR_GBP": 0.85
            }
            latest_price = mock_prices.get(instrument, 1.0)
        
        # Calculate units for each USD amount
        row = f"{instrument:<10} | {latest_price:<8.4f} |"
        for amount in usd_amounts:
            units = 0
            try:
                # Direct calculation based on instrument type
                if instrument.startswith("USD_"):
                    if instrument.endswith("JPY"):
                        units = round(amount * (latest_price * 0.01))
                    else:
                        units = round(amount * latest_price)
                elif instrument.endswith("USD"):
                    units = round(amount / latest_price)
                else:
                    # For crosses, use an approximation
                    units = round(amount)
            except Exception:
                units = 0
            
            row += f" {units:<6} |"
        
        print(row)
    
    print("=" * 100)
    print("Note: This table shows approximate units required to achieve the USD amount for each instrument.")
    print("      Actual values may vary based on current market prices and cross-rate calculations.")
    print("      Units are always rounded to the nearest whole number.")

def main():
    """Main function"""
    args = parse_args()
    
    # Show reference table if requested
    if args.show_reference:
        show_reference_table()
        return 0
    
    # Check if OANDA API is available
    if not OANDA_AVAILABLE and not args.dry_run:
        logger.error("OANDA API is required for live trading. Install with: pip install oandapyV20")
        return 1
    
    # Parse positions from terminal log
    logger.info("Parsing positions from terminal log")
    positions = parse_terminal_log_positions()
    
    # Save positions to file
    file_path = save_positions_to_file(positions)
    
    # If dry run, we're done
    if args.dry_run:
        logger.info("Dry run completed. Positions saved but not executed.")
        return 0
    
    # Initialize OANDA trader using environment variables
    try:
        trader = OandaTrader(
            account_id=args.account_id,  # Will fall back to OANDA_DEMO_ACCOUNT_ID env var if not provided
            access_token=args.api_token  # Will fall back to OANDA_DEMO_KEY env var if not provided
        )
        
        # Print env vars for debugging if we have issues
        logger.info(f"OANDA environment variables set: DEMO_ACCOUNT_ID: {'Yes' if os.environ.get('OANDA_DEMO_ACCOUNT_ID') else 'No'}, DEMO_KEY: {'Yes' if os.environ.get('OANDA_DEMO_KEY') else 'No'}")
        
        # If verify-only flag is set, exit after successful connection
        if args.verify_only:
            logger.info("Account verification successful. Exiting without syncing positions.")
            return 0
        
    except Exception as e:
        logger.error(f"Failed to initialize OANDA trader: {e}")
        logger.error("Make sure OANDA_DEMO_ACCOUNT_ID and OANDA_DEMO_KEY environment variables are set")
        return 1
    
    # Sync positions (calculate differences and place only necessary orders)
    logger.info("Syncing positions with OANDA")
    result = sync_positions(trader, positions)
    
    if result:
        logger.info("Successfully synchronized positions with OANDA")
        return 0
    else:
        logger.error("Failed to synchronize positions")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 