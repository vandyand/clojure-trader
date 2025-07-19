"""
Real implementation of the OANDA API using oandapyV20 library and environment variables.
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.orders as orders
from oandapyV20.exceptions import V20Error

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("oanda_api")

# Get OANDA API credentials from environment variables
OANDA_LIVE_KEY = os.environ.get('OANDA_LIVE_KEY')
OANDA_DEMO_KEY = os.environ.get('OANDA_DEMO_KEY')
OANDA_LIVE_URL = os.environ.get('OANDA_LIVE_URL')
OANDA_DEMO_URL = os.environ.get('OANDA_DEMO_URL')
OANDA_LIVE_ACCOUNT_ID = os.environ.get('OANDA_LIVE_ACCOUNT_ID')
OANDA_DEMO_ACCOUNT_ID = os.environ.get('OANDA_DEMO_ACCOUNT_ID')

# Determine if we're using live or demo
USE_LIVE = os.environ.get('USE_LIVE', 'false').lower() == 'true'

# Configure OANDA API client
API_KEY = OANDA_LIVE_KEY if USE_LIVE else OANDA_DEMO_KEY
ACCOUNT_ID = OANDA_LIVE_ACCOUNT_ID if USE_LIVE else OANDA_DEMO_ACCOUNT_ID
ENVIRONMENT = "live" if USE_LIVE else "practice"

# Create API client instance
try:
    client = oandapyV20.API(access_token=API_KEY, environment=ENVIRONMENT)
    logger.info(f"OANDA API client initialized in {ENVIRONMENT} mode")
except Exception as e:
    logger.error(f"Failed to initialize OANDA API client: {str(e)}")
    raise

# Price cache to reduce API calls
price_cache = {}
PRICE_CACHE_TTL = 2  # Cache TTL in seconds

def get_latest_price(instrument: str) -> float:
    """
    Get the latest price for an instrument from OANDA API.
    
    Args:
        instrument: The instrument to get the price for (e.g., "EUR_USD")
        
    Returns:
        The latest price as a float
    """
    global price_cache
    
    # Check if we have a cached price that's still valid
    cache_key = instrument
    current_time = time.time()
    if cache_key in price_cache and (current_time - price_cache[cache_key]['timestamp']) < PRICE_CACHE_TTL:
        return price_cache[cache_key]['price']
    
    # No valid cache, fetch from API
    try:
        params = {"instruments": instrument}
        request = pricing.PricingInfo(accountID=ACCOUNT_ID, params=params)
        response = client.request(request)
        
        if 'prices' in response and response['prices']:
            price_data = response['prices'][0]
            if 'closeoutAsk' in price_data and 'closeoutBid' in price_data:
                # Calculate mid price
                price = (float(price_data['closeoutAsk']) + float(price_data['closeoutBid'])) / 2
                # Update cache
                price_cache[cache_key] = {'price': price, 'timestamp': current_time}
                return price
            else:
                logger.warning(f"Missing price data for {instrument}: {price_data}")
                return 0.0
        else:
            logger.warning(f"No prices returned for {instrument}")
            return 0.0
            
    except V20Error as e:
        logger.error(f"OANDA API error for {instrument}: {e}")
        return 0.0
    except Exception as e:
        logger.error(f"Unexpected error getting price for {instrument}: {e}")
        return 0.0

def get_candles(instrument: str, granularity: str, from_time: str, to_time: str) -> List[Dict[str, Any]]:
    """
    Get price candles for an instrument from OANDA API.
    
    Args:
        instrument: The instrument to get candles for
        granularity: The candlestick granularity (e.g., "D" for daily)
        from_time: Start time for the range
        to_time: End time for the range
        
    Returns:
        List of candle dictionaries
    """
    try:
        params = {
            "granularity": granularity,
            "from": from_time,
            "to": to_time,
            "price": "M"  # Midpoint data
        }
        
        # Create request
        request = instruments.InstrumentsCandles(
            instrument=instrument,
            params=params
        )
        
        # Send request
        response = client.request(request)
        
        # Return candles
        return response.get('candles', [])
        
    except V20Error as e:
        logger.error(f"OANDA API error getting candles for {instrument}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting candles for {instrument}: {e}")
        return []

def get_account_nav() -> float:
    """
    Get the account net asset value.
    
    Returns:
        The account NAV
    """
    try:
        request = accounts.AccountSummary(accountID=ACCOUNT_ID)
        response = client.request(request)
        
        if 'account' in response and 'NAV' in response['account']:
            return float(response['account']['NAV'])
        else:
            logger.warning("NAV not found in account summary")
            return 0.0
            
    except V20Error as e:
        logger.error(f"OANDA API error getting account NAV: {e}")
        return 0.0
    except Exception as e:
        logger.error(f"Unexpected error getting account NAV: {e}")
        return 0.0

def get_open_positions() -> List[Dict[str, Any]]:
    """
    Get all open positions for the account.
    
    Returns:
        List of open position dictionaries
    """
    try:
        request = positions.OpenPositions(accountID=ACCOUNT_ID)
        response = client.request(request)
        
        return response.get('positions', [])
        
    except V20Error as e:
        logger.error(f"OANDA API error getting open positions: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting open positions: {e}")
        return []

def create_order(instrument: str, units: float, type: str = "MARKET") -> Dict[str, Any]:
    """
    Create a new order.
    
    Args:
        instrument: The instrument to trade
        units: Number of units (positive for buy, negative for sell)
        type: Order type (default: "MARKET")
        
    Returns:
        Order response dictionary
    """
    try:
        # Create order data
        data = {
            "order": {
                "type": type,
                "instrument": instrument,
                "units": str(units)
            }
        }
        
        # Create request
        request = orders.OrderCreate(accountID=ACCOUNT_ID, data=data)
        
        # Send request
        response = client.request(request)
        
        return response
        
    except V20Error as e:
        logger.error(f"OANDA API error creating order for {instrument}: {e}")
        return {"errorMessage": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error creating order for {instrument}: {e}")
        return {"errorMessage": str(e)}

def close_position(instrument: str) -> Dict[str, Any]:
    """
    Close an open position for an instrument.
    
    Args:
        instrument: The instrument to close position for
        
    Returns:
        Response dictionary
    """
    try:
        # We need to specify whether to close long or short positions
        # First, get current position
        request = positions.OpenPositions(accountID=ACCOUNT_ID)
        response = client.request(request)
        
        for position in response.get('positions', []):
            if position['instrument'] == instrument:
                # Determine if long or short position
                long_units = position.get('long', {}).get('units', '0')
                short_units = position.get('short', {}).get('units', '0')
                
                data = {}
                if float(long_units) > 0:
                    data['longUnits'] = 'ALL'
                if float(short_units) < 0:
                    data['shortUnits'] = 'ALL'
                
                # If we have units to close, send the request
                if data:
                    close_request = positions.PositionClose(
                        accountID=ACCOUNT_ID,
                        instrument=instrument,
                        data=data
                    )
                    return client.request(close_request)
                
        return {"message": f"No open position found for {instrument}"}
        
    except V20Error as e:
        logger.error(f"OANDA API error closing position for {instrument}: {e}")
        return {"errorMessage": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error closing position for {instrument}: {e}")
        return {"errorMessage": str(e)}

def get_binance_account_usd_amount() -> float:
    """
    This is a placeholder for Binance integration.
    In a real system, this would connect to Binance API.
    
    Returns:
        Default 500.0 as a placeholder
    """
    logger.warning("Using placeholder for Binance account balance - not implemented yet")
    return 500.0 