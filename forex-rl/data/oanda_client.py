# data/oanda_client.py
import oandapyV20
import oandapyV20.endpoints.instruments as oanda_instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.pricing as oanda_pricing
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import requests
from config.settings import config
from config.forex_pairs import FOREX_PAIRS
from config.oanda_config import oanda_config
import pytz

# Set up logging
logging.basicConfig(level=getattr(logging, config.log_level), format=config.log_format)
logger = logging.getLogger(__name__)

class OandaClient:
    """
    Client for interacting with OANDA API
    
    Features:
    - Historical data retrieval
    - Real-time price streaming
    - Order management
    - Position tracking
    - Account information
    """
    
    def __init__(self):
        """Initialize OANDA API client"""
        self.client = oandapyV20.API(
            access_token=oanda_config.api_key,
            environment=oanda_config.environment
        )
        self.account_id = oanda_config.account_id
        logger.info(f"Initialized OANDA client for account {self.account_id}")
    
    def get_historical_data(
        self,
        instrument: str,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "M5"  # 5-minute candles
    ) -> pd.DataFrame:
        """
        Get historical price data
        
        Args:
            instrument: Currency pair (e.g., "EUR_USD")
            start_time: Start time
            end_time: End time
            granularity: Candle granularity
            
        Returns:
            DataFrame with OHLCV data
        """
        params = {
            "from": start_time.isoformat(),
            "to": end_time.isoformat(),
            "granularity": granularity,
            "price": "M"  # Midpoint candles
        }
        
        try:
            r = oanda_instruments.InstrumentsCandles(
                instrument=instrument,
                params=params
            )
            self.client.request(r)
            
            # Convert to DataFrame
            data = []
            for candle in r.response['candles']:
                if candle['complete']:
                    data.append({
                        'timestamp': pd.to_datetime(candle['time']),
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': int(candle['volume'])
                    })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary information"""
        try:
            r = accounts.AccountSummary(self.account_id)
            self.client.request(r)
            return r.response['account']
        except Exception as e:
            logger.error(f"Error fetching account summary: {e}")
            raise
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            r = positions.OpenPositions(self.account_id)
            self.client.request(r)
            return r.response['positions']
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    def place_order(
        self,
        instrument: str,
        units: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place a new order
        
        Args:
            instrument: Currency pair
            units: Number of units (positive for long, negative for short)
            order_type: Order type (MARKET, LIMIT, etc.)
            price: Price for limit orders
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order response
        """
        order_data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "type": order_type,
                "positionFill": "DEFAULT"
            }
        }
        
        # Add optional parameters
        if price:
            order_data["order"]["price"] = str(price)
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {"price": str(stop_loss)}
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {"price": str(take_profit)}
        
        try:
            r = orders.OrderCreate(self.account_id, data=order_data)
            self.client.request(r)
            return r.response
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise
    
    def close_position(self, instrument: str) -> Dict[str, Any]:
        """Close all positions for an instrument"""
        try:
            r = positions.PositionClose(self.account_id, instrument)
            self.client.request(r)
            return r.response
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise
    
    def get_order_book(self, instrument: str) -> Dict[str, Any]:
        """Get current order book for an instrument"""
        try:
            r = oanda_instruments.InstrumentsOrderBook(instrument=instrument)
            self.client.request(r)
            return r.response
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            raise
    
    def get_pricing(self, instruments: List[str]) -> Dict[str, Any]:
        """Get current pricing for instruments"""
        try:
            params = {"instruments": ",".join(instruments)}
            r = oanda_pricing.PricingInfo(
                accountID=self.account_id,
                params=params
            )
            self.client.request(r)
            return r.response
        except Exception as e:
            logger.error(f"Error fetching pricing: {e}")
            raise


def test_oanda_client():
    """Test OANDA client functionality"""
    logger.info("Testing OANDA client...")
    
    client = OandaClient()
    
    # Test account summary
    account = client.get_account_summary()
    logger.info(f"Account balance: {account['balance']}")
    
    # Test historical data
    end_time = datetime.now(pytz.UTC)
    start_time = end_time - timedelta(days=1)
    data = client.get_historical_data("EUR_USD", start_time, end_time)
    logger.info(f"Retrieved {len(data)} historical candles")
    
    # Test pricing
    pricing = client.get_pricing(["EUR_USD", "GBP_USD"])
    logger.info("Current prices:")
    for price in pricing['prices']:
        logger.info(f"  {price['instrument']}: {price['bids'][0]['price']} / {price['asks'][0]['price']}")
    
    logger.info("✓ OANDA client test completed")
    return True


if __name__ == "__main__":
    test_oanda_client()

class OandaDataClient:
    """
    OANDA API client for fetching forex data
    Handles authentication, rate limiting, and error recovery
    """

    def __init__(self, api_key: str = None, account_id: str = None, environment: str = None):
        """
        Initialize OANDA client
        
        Args:
            api_key: OANDA API key (defaults to config)
            account_id: OANDA account ID (defaults to config)
            environment: 'practice' or 'live' (defaults to config)
        """
        self.api_key = api_key or config.oanda_api_key
        self.account_id = account_id or config.oanda_account_id
        self.environment = environment or config.oanda_environment

        if not self.api_key:
            raise ValueError("OANDA API key is required. Set OANDA_DEMO_KEY environment variable.")
        
        if not self.account_id:
            raise ValueError("OANDA Account ID is required. Set OANDA_DEMO_ACCOUNT_ID environment variable.")

        # Initialize API client
        self.api = API(access_token=self.api_key, environment=self.environment)
        
        # Rate limiting (OANDA allows 100 requests per second)
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial retry delay in seconds
        
        logger.info(f"Initialized OANDA client for {self.environment} environment")

    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _make_request_with_retry(self, request) -> dict:
        """
        Make API request with retry logic
        
        Args:
            request: OANDA API request object
            
        Returns:
            API response dictionary
        """
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                response = self.api.request(request)
                return response
                
            except Exception as e:
                logger.warning(f"API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for request")
                    raise e

    def test_connection(self) -> bool:
        """
        Test API connection and authentication
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            request = accounts.AccountDetails(accountID=self.account_id)
            response = self._make_request_with_retry(request)
            
            if 'account' in response:
                logger.info("OANDA connection test successful")
                return True
            else:
                logger.error("OANDA connection test failed: Invalid response")
                return False
                
        except Exception as e:
            logger.error(f"OANDA connection test failed: {e}")
            return False

    def fetch_historical_data(self,
                            instrument: str,
                            granularity: str = "D",
                            count: int = 5000,
                            from_time: datetime = None,
                            to_time: datetime = None) -> pd.DataFrame:
        """
        Fetch historical candlestick data for an instrument

        Args:
            instrument: Forex pair (e.g., "EUR_USD")
            granularity: Timeframe ("D" for daily, "H1" for hourly, etc.)
            count: Number of candles to fetch (max 5000)
            from_time: Start time (optional)
            to_time: End time (optional)

        Returns:
            DataFrame with OHLCV data indexed by time
        """
        try:
            # Prepare request parameters
            params = {
                "granularity": granularity,
                "count": min(count, 5000)  # OANDA limit
            }
            
            # Add time range if specified
            if from_time:
                params["from"] = from_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            if to_time:
                params["to"] = to_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            # Make request
            request = oanda_instruments.InstrumentsCandles(
                instrument=instrument,
                params=params
            )

            response = self._make_request_with_retry(request)
            candles = response.get('candles', [])

            if not candles:
                logger.warning(f"No candles returned for {instrument}")
                return pd.DataFrame()

            # Convert to DataFrame
            data = []
            for candle in candles:
                if candle['complete']:  # Only use complete candles
                    data.append({
                        'time': pd.to_datetime(candle['time']),
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': int(candle['volume'])
                    })

            if not data:
                logger.warning(f"No complete candles found for {instrument}")
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame(data)
            df.set_index('time', inplace=True)
            df.sort_index(inplace=True)

            logger.info(f"Fetched {len(df)} candles for {instrument} ({granularity})")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {instrument}: {e}")
            return pd.DataFrame()

    def fetch_multiple_instruments(self,
                                 instruments: List[str] = None,
                                 granularity: str = "D",
                                 count: int = 5000,
                                 from_time: datetime = None,
                                 to_time: datetime = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple instruments

        Args:
            instruments: List of forex pairs (defaults to all configured pairs)
            granularity: Timeframe
            count: Number of candles per instrument
            from_time: Start time (optional)
            to_time: End time (optional)

        Returns:
            Dictionary mapping instrument to DataFrame
        """
        if instruments is None:
            instruments = FOREX_PAIRS

        data = {}
        total_instruments = len(instruments)

        logger.info(f"Fetching data for {total_instruments} instruments...")

        for i, instrument in enumerate(instruments, 1):
            logger.info(f"Fetching data for {instrument} ({i}/{total_instruments})")
            
            df = self.fetch_historical_data(
                instrument=instrument,
                granularity=granularity,
                count=count,
                from_time=from_time,
                to_time=to_time
            )

            if not df.empty:
                data[instrument] = df
                logger.info(f"✓ {instrument}: {len(df)} candles")
            else:
                logger.warning(f"✗ {instrument}: No data retrieved")

        logger.info(f"Data fetching complete. Retrieved data for {len(data)}/{total_instruments} instruments")
        return data

    def get_latest_prices(self, instruments: List[str] = None) -> Dict[str, float]:
        """
        Get latest prices for instruments
        
        Args:
            instruments: List of forex pairs (defaults to all configured pairs)
            
        Returns:
            Dictionary mapping instrument to latest price
        """
        if instruments is None:
            instruments = FOREX_PAIRS

        prices = {}
        
        for instrument in instruments:
            try:
                # Fetch just the latest candle
                df = self.fetch_historical_data(instrument, count=1)
                if not df.empty:
                    prices[instrument] = df['close'].iloc[-1]
                    
            except Exception as e:
                logger.error(f"Error getting latest price for {instrument}: {e}")
                
        return prices

    def validate_instruments(self, instruments: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate that instruments are available for trading
        
        Args:
            instruments: List of instrument names to validate
            
        Returns:
            Tuple of (valid_instruments, invalid_instruments)
        """
        valid = []
        invalid = []
        
        for instrument in instruments:
            try:
                # Try to fetch a small amount of data
                df = self.fetch_historical_data(instrument, count=1)
                if not df.empty:
                    valid.append(instrument)
                else:
                    invalid.append(instrument)
                    
            except Exception as e:
                logger.warning(f"Instrument {instrument} validation failed: {e}")
                invalid.append(instrument)
                
        logger.info(f"Instrument validation: {len(valid)} valid, {len(invalid)} invalid")
        return valid, invalid

    def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Dictionary with account details
        """
        try:
            request = accounts.AccountDetails(accountID=self.account_id)
            response = self._make_request_with_retry(request)
            return response.get('account', {})
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

# Convenience function for quick data fetching
def fetch_forex_data(instruments: List[str] = None, 
                    days: int = None,
                    count: int = 5000) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to fetch forex data
    
    Args:
        instruments: List of forex pairs (defaults to all)
        days: Number of days of historical data
        count: Number of candles (used if days not specified)
        
    Returns:
        Dictionary of DataFrames
    """
    client = OandaDataClient()
    
    # Test connection first
    if not client.test_connection():
        logger.error("Failed to connect to OANDA API")
        return {}
    
    # Calculate time range if days specified
    from_time = None
    if days:
        from_time = datetime.now() - timedelta(days=days)
        count = None  # Don't use count if using time range
    
    return client.fetch_multiple_instruments(
        instruments=instruments,
        count=count,
        from_time=from_time
    ) 