#!/usr/bin/env python3
import os
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("oanda_trader")

# --- OANDA API Import START ---
API = None
AccountDetails = None
OrderCreate = None
# OrdersList = None # This specific import seems to cause issues, let's see if it's critical or if oandapyV20 handles it differently now
OpenPositions = None
PositionClose = None
trades = None
OANDA_AVAILABLE = False

def _import_oanda_api():
    global API, AccountDetails, OrderCreate, OpenPositions, PositionClose, trades, OANDA_AVAILABLE
    try:
        # Ensure current environment paths are checked
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
             sys.path.insert(0, current_dir)
        for site_packages_dir in sys.path:
            if "site-packages" in site_packages_dir and site_packages_dir not in sys.path:
                sys.path.insert(0, site_packages_dir)

        from oandapyV20 import API as oanda_API
        from oandapyV20.endpoints.accounts import AccountDetails as oanda_AccountDetails
        from oandapyV20.endpoints.orders import OrderCreate as oanda_OrderCreate #, OrdersList as oanda_OrdersList # Temporarily comment out OrdersList
        from oandapyV20.endpoints.positions import OpenPositions as oanda_OpenPositions, PositionClose as oanda_PositionClose
        import oandapyV20.endpoints.trades as oanda_trades
        
        API = oanda_API
        AccountDetails = oanda_AccountDetails
        OrderCreate = oanda_OrderCreate
        # OrdersList = oanda_OrdersList # Temporarily comment out OrdersList
        OpenPositions = oanda_OpenPositions
        PositionClose = oanda_PositionClose
        trades = oanda_trades
        OANDA_AVAILABLE = True
        logger.info("oandapyV20 components imported successfully by _import_oanda_api")
        return True
    except ImportError as e:
        logger.error(f"oandapyV20 not found or specific components missing during _import_oanda_api. Error: {e}.")
        logger.error(f"Current sys.path: {sys.path}")
        OANDA_AVAILABLE = False
        return False

_import_oanda_api() # Attempt import at module load time
# --- OANDA API Import END ---

class OandaTrader:
    """Class to interact with OANDA API for trading"""
    
    def __init__(self, account_id=None, access_token=None, practice=True):
        """Initialize with OANDA credentials"""
        if not OANDA_AVAILABLE:
            raise ImportError("oandapyV20 is not installed or essential components are missing. Please install/reinstall it. Error logged during import attempt.")

        self.practice = practice
        if practice:
            self.account_id = account_id or os.environ.get('OANDA_DEMO_ACCOUNT_ID')
            self.access_token = access_token or os.environ.get('OANDA_DEMO_KEY')
        else:
            self.account_id = account_id or os.environ.get('OANDA_LIVE_ACCOUNT_ID')
            self.access_token = access_token or os.environ.get('OANDA_LIVE_KEY')

        if not self.account_id:
            logger.error("No OANDA account ID provided. Set OANDA_DEMO_ACCOUNT_ID (for practice) or OANDA_LIVE_ACCOUNT_ID (for live) environment variable or pass as parameter.")
            raise ValueError("OANDA account ID required")
            
        if not self.access_token:
            logger.error("No OANDA API token provided. Set OANDA_DEMO_KEY (for practice) or OANDA_LIVE_KEY (for live) environment variable or pass as parameter.")
            raise ValueError("OANDA API token required")
        
        environment_name = "practice" if practice else "live"
        self.api = API(access_token=self.access_token, environment=environment_name)
        logger.info(f"Initialized OANDA API client for {environment_name} environment")
        self._verify_account()
    
    def _verify_account(self):
        try:
            r = AccountDetails(accountID=self.account_id)
            self.api.request(r)
            logger.info(f"Successfully connected to OANDA account {self.account_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OANDA account: {e}")
            raise
    
    def get_account_info(self):
        try:
            r = AccountDetails(accountID=self.account_id)
            return self.api.request(r)
        except Exception as e:
            logger.error(f"Error getting account details: {e}")
            return None
    
    def close_all_positions(self):
        try:
            r = OpenPositions(accountID=self.account_id)
            response = self.api.request(r)
            positions = response.get("positions", [])
            logger.info(f"Found {len(positions)} open positions")
            for position in positions:
                instrument = position.get("instrument")
                long_units = position.get("long", {}).get("units", "0")
                short_units = position.get("short", {}).get("units", "0")
                if long_units != "0":
                    self.api.request(PositionClose(accountID=self.account_id, instrument=instrument, data={"longUnits": "ALL"}))
                    logger.info(f"Closed long position for {instrument}")
                if short_units != "0":
                    self.api.request(PositionClose(accountID=self.account_id, instrument=instrument, data={"shortUnits": "ALL"}))
                    logger.info(f"Closed short position for {instrument}")
            logger.info("All positions closed")
            return True
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False
    
    def place_order(self, instrument, units, take_profit=None, stop_loss=None):
        try:
            order_config = {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT"
            }
            if take_profit:
                order_config["takeProfitOnFill"] = {"price": str(take_profit)}
            if stop_loss:
                order_config["stopLossOnFill"] = {"price": str(stop_loss)}
            
            data = {"order": order_config}
            r = OrderCreate(accountID=self.account_id, data=data)
            response = self.api.request(r)
            order_id = response.get("orderCreateTransaction", {}).get("id")
            logger.info(f"Placed {instrument} order for {units} units, order ID: {order_id}")
            return order_id
        except Exception as e:
            logger.error(f"Error placing order for {instrument}: {e}")
            return None

# Main execution / script functions (parse_args, get_latest_signal_file, etc.)
# These should be outside the OandaTrader class and use it.

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="OANDA Trader")
    
    parser.add_argument("--account-id", type=str, help="OANDA account ID (overrides env var)")
    parser.add_argument("--api-token", type=str, help="OANDA API token (overrides env var)")
    parser.add_argument("--practice", action="store_true", default=True,
                       help="Use practice environment (default: True). If false, uses live credentials.")
    parser.add_argument("--signal-file", type=str, 
                       help="JSON signal file to use (default: latest)")
    parser.add_argument("--close-positions", action="store_true",
                       help="Close all existing positions first")
    parser.add_argument("--account-size", type=float, default=1000.0,
                       help="Account size in USD (for informational purposes in signals)")
    parser.add_argument("--verify-only", action="store_true",
                       help="Only verify account connection, don't place trades")
    
    return parser.parse_args()

def get_latest_signal_file():
    """Get the latest signal file from the signals directory"""
    try:
        signals_dir = os.path.join(parent_dir, "signals")
        if not os.path.exists(signals_dir):
            logger.error(f"Signals directory not found: {signals_dir}")
            return None
        signal_files = [f for f in os.listdir(signals_dir) if f.endswith(".json")]
        if not signal_files:
            logger.error("No signal files found in signals directory")
            return None
        latest_file = sorted(signal_files)[-1]
        return os.path.join(signals_dir, latest_file)
    except Exception as e:
        logger.error(f"Error finding latest signal file: {e}")
        return None

def load_signals(file_path):
    """Load trading signals from a JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Loaded signals from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading signals from {file_path}: {e}")
        return None

def place_trades_from_signals(trader, signals):
    """Place trades based on signals from a loaded signal file"""
    positions_to_trade = signals.get("positions", [])
    if not positions_to_trade:
        logger.warning("No positions found in signals file")
        return False
    
    success_count = 0
    fail_count = 0
    
    for position in positions_to_trade:
        instrument = position.get("instrument")
        direction = position.get("direction")
        if direction == "NEUTRAL":
            logger.info(f"Skipping {instrument}: NEUTRAL position")
            continue
        
        units = position.get("position_size", 0)
        if direction == "SHORT":
            units = -abs(units)
        
        # Scale units for OANDA (e.g., if position_size is a small float)
        # Assuming position_size from signals might be small abstract values
        # OANDA typically requires integer units, often in multiples (e.g. 100, 1000)
        # This logic might need refinement based on how `position_size` is determined.
        adjusted_units = int(units * 100) # Example: scale by 100. Adjust if needed.
        if adjusted_units == 0: # Avoid placing zero unit orders if scaling results in 0
            adjusted_units = 100 if units > 0 else -100 # Default to a minimum trade size
            logger.warning(f"Adjusted units for {instrument} to {adjusted_units} due to scaling resulting in zero.")

        order_id = trader.place_order(instrument, adjusted_units)
        if order_id:
            success_count += 1
        else:
            fail_count += 1
            
    logger.info(f"Attempted to place {success_count + fail_count} orders. Successful: {success_count}, Failed: {fail_count}")
    return success_count > 0

def main():
    """Main function for oanda_trader.py script execution"""
    args = parse_args()
    
    if not OANDA_AVAILABLE:
        return 1 # Error already logged
    
    try:
        trader = OandaTrader(
            account_id=args.account_id, # Allow override from CLI
            access_token=args.api_token, # Allow override from CLI
            practice=args.practice
        )
    except Exception as e:
        logger.error(f"Failed to initialize OANDA trader: {e}")
        logger.error("Ensure OANDA_DEMO_ACCOUNT_ID & OANDA_DEMO_KEY (for practice) or OANDA_LIVE_ACCOUNT_ID & OANDA_LIVE_KEY (for live) are set, or pass --account-id and --api-token.")
        return 1

    if args.verify_only:
        if OANDA_AVAILABLE and trader:
             logger.info("Account verification successful. Exiting.")
        else:
             logger.info("OANDA API not available or trader not initialized. Exiting verify_only.")
        return 0

    if args.close_positions:
        logger.info("Closing all existing positions...")
        trader.close_all_positions()

    if args.signal_file:
        signal_file_to_use = args.signal_file
    else:
        signal_file_to_use = get_latest_signal_file()
        if not signal_file_to_use:
            logger.error("No signal file specified and couldn't find the latest one.")
            return 1
            
    signals = load_signals(signal_file_to_use)
    if not signals:
        return 1

    logger.info("Placing trades based on signals...")
    if place_trades_from_signals(trader, signals):
        logger.info("Trading tasks based on signal file completed successfully.")
        return 0
    else:
        logger.error("Failed to complete all trading tasks based on signal file.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 