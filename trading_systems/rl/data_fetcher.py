import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import logging
from typing import List, Dict, Any, Tuple, Optional

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from api.oanda_api import get_candles, get_latest_price
from rl.feature_engineering import calculate_features
from rl.data.fetch_etf_data import fetch_historical_etf_data, fetch_latest_etf_price

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"data_fetcher_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("data_fetcher")

class MarketDataFetcher:
    """
    Fetches and prepares market data for all instruments including:
    - Latest price data
    - Feature calculation
    
    Handles both FOREX (via OANDA) and ETF (via yfinance) data sources.
    """
    
    def __init__(self, instruments: List[str] = None, 
                 feature_params: Dict[str, Any] = None, 
                 history_days: int = 400,
                 etf_symbols: List[str] = None):
        """
        Initialize the data fetcher
        
        Args:
            instruments: List of instruments to fetch data for (default: PAIRS_BY_LIQUIDITY_OANDA)
            feature_params: Parameters for feature calculation
            history_days: Number of days of historical data to fetch
            etf_symbols: Additional ETF symbols to include
        """
        self.forex_instruments = PAIRS_BY_LIQUIDITY_OANDA
        self.etf_symbols = etf_symbols or []
        
        # Combine all instruments
        self.instruments = instruments or (self.forex_instruments + self.etf_symbols)
        self.history_days = history_days
        
        # Default feature parameters
        self.feature_params = {
            'price_features': True,
            'volume_features': True,
            'ma_periods': [3, 8, 13, 21, 34, 55, 89, 144, 233, 377],
            'roc_periods': [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377],
            'std_periods': [3, 5, 8, 13, 21, 34, 55, 89, 144, 233],
            'bb_periods': [5, 13, 21, 34, 55],
            'rsi_periods': [2, 3, 5, 8, 13, 21, 34],
            'obv_periods': [3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
        }
        
        # Update with user-provided params if available
        if feature_params:
            self.feature_params.update(feature_params)
            
        # Cache for price data and features
        self.price_data_cache = {}
        self.feature_cache = {}
        self.last_update_time = {}
    
    def is_forex(self, instrument: str) -> bool:
        """
        Determine if an instrument is a forex pair or ETF.
        
        Args:
            instrument: The instrument to check
            
        Returns:
            True if forex (OANDA), False if ETF/stock
        """
        return instrument in self.forex_instruments
        
    def fetch_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch price data for the specified instrument from the appropriate source
        
        Args:
            instrument: The instrument to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        try:
            logger.info(f"Fetching price data for {instrument}")
            
            # Handle forex (OANDA) vs ETF (yfinance) differently
            if self.is_forex(instrument):
                return self._fetch_forex_price_data(instrument)
            else:
                return self._fetch_etf_price_data(instrument)
                
        except Exception as e:
            logger.error(f"Error fetching data for {instrument}: {str(e)}")
            return None
    
    def _fetch_forex_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch forex price data from OANDA
        
        Args:
            instrument: The forex instrument to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        try:
            # Calculate start date for historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.history_days)
            
            # Convert to string format
            start_date_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
            end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Fetch candles from OANDA
            candles = get_candles(instrument, "D", start_date_str, end_date_str)
            
            if not candles:
                logger.warning(f"No candles returned for {instrument}")
                return None
                
            # Parse candles into DataFrame
            data = []
            for candle in candles:
                timestamp = pd.to_datetime(candle["time"])
                
                # Extract OHLCV data
                ohlc = candle["mid"] if "mid" in candle else candle["bid"]
                row = {
                    "time": timestamp,
                    "open": float(ohlc["o"]),
                    "high": float(ohlc["h"]),
                    "low": float(ohlc["l"]),
                    "close": float(ohlc["c"]),
                    "volume": float(candle.get("volume", 0)),
                }
                data.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(data)
            df.set_index("time", inplace=True)
            df.sort_index(inplace=True)
            
            # Store in cache
            self.price_data_cache[instrument] = df
            self.last_update_time[instrument] = datetime.now()
            
            logger.info(f"Fetched {len(df)} candles for {instrument}")
            return df
        
        except Exception as e:
            logger.error(f"Error fetching forex data for {instrument}: {str(e)}")
            return None
    
    def _fetch_etf_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch ETF price data from yfinance
        
        Args:
            instrument: The ETF symbol to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        try:
            # Use our yfinance wrapper to get the data
            # Set period to fetch enough days of history
            period_str = f"{self.history_days}d"
            
            # Get data
            df = fetch_historical_etf_data(
                ticker=instrument, 
                period=period_str, 
                interval="1d",
                use_cache=True
            )
            
            if df is None or df.empty:
                logger.warning(f"No data returned for ETF {instrument}")
                return None
            
            # Standardize column names and index to match our format expectations
            # (yfinance uses 'Open', 'High', etc. and we use 'open', 'high', etc.)
            if df.index.name != 'time':
                df = df.rename_axis('time')
            
            # Store in cache
            self.price_data_cache[instrument] = df
            self.last_update_time[instrument] = datetime.now()
            
            logger.info(f"Fetched {len(df)} days of data for ETF {instrument}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching ETF data for {instrument}: {str(e)}")
            return None
    
    def calculate_instrument_features(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Calculate features for the specified instrument
        
        Args:
            instrument: The instrument to calculate features for
            
        Returns:
            DataFrame with calculated features or None if error
        """
        try:
            # Get price data (fetch if not cached)
            if instrument not in self.price_data_cache:
                price_data = self.fetch_price_data(instrument)
                if price_data is None:
                    return None
            else:
                price_data = self.price_data_cache[instrument]
            
            logger.info(f"Calculating features for {instrument}")
            
            # Calculate features
            features_df = calculate_features(
                price_data, 
                instrument, 
                **self.feature_params
            )
            
            # Store in cache
            self.feature_cache[instrument] = features_df
            
            logger.info(f"Calculated {features_df.shape[1]} features for {instrument}")
            return features_df
            
        except Exception as e:
            logger.error(f"Error calculating features for {instrument}: {str(e)}")
            return None
    
    def get_latest_features(self, instrument: str, recalculate: bool = False) -> Optional[pd.Series]:
        """
        Get the latest features for the specified instrument
        
        Args:
            instrument: The instrument to get features for
            recalculate: Force recalculation even if cached
            
        Returns:
            Series with latest features or None if error
        """
        # Check cache expiry (recalculate after 24 hours)
        cache_expired = False
        if instrument in self.last_update_time:
            cache_age = datetime.now() - self.last_update_time[instrument]
            cache_expired = cache_age.total_seconds() > 24 * 60 * 60  # 24 hours
        
        if recalculate or instrument not in self.feature_cache or cache_expired:
            features_df = self.calculate_instrument_features(instrument)
            if features_df is None:
                return None
        else:
            features_df = self.feature_cache[instrument]
        
        # Get the latest row
        latest_features = features_df.iloc[-1]
        return latest_features
    
    def get_all_latest_features(self, recalculate: bool = False) -> Dict[str, pd.Series]:
        """
        Get latest features for all instruments
        
        Args:
            recalculate: Force recalculation even if cached
            
        Returns:
            Dictionary of instrument -> Series with latest features
        """
        results = {}
        
        for instrument in self.instruments:
            try:
                features = self.get_latest_features(instrument, recalculate)
                if features is not None:
                    results[instrument] = features
            except Exception as e:
                logger.error(f"Error getting features for {instrument}: {str(e)}")
        
        return results
    
    def get_latest_price_for_instrument(self, instrument: str) -> Optional[float]:
        """
        Get the latest price for an instrument
        
        Args:
            instrument: The instrument to get the price for
            
        Returns:
            Latest price or None if error
        """
        try:
            # Use different API based on instrument type
            if self.is_forex(instrument):
                # Use OANDA API
                price = get_latest_price(instrument)
            else:
                # Use yfinance API
                price = fetch_latest_etf_price(instrument)
                
            return price
                
        except Exception as e:
            logger.error(f"Error getting latest price for {instrument}: {str(e)}")
            return None
    
    def prepare_feature_vector(self) -> Optional[np.ndarray]:
        """
        Prepare a feature vector for all instruments
        
        Returns:
            Feature vector for RL model or None if error
        """
        try:
            # Get features for all instruments
            all_features = self.get_all_latest_features()
            
            if not all_features:
                logger.error("No features available for any instrument")
                return None
            
            # Prepare feature vector in the correct order
            feature_vector = []
            
            for instrument in self.instruments:
                if instrument in all_features:
                    # Add features
                    instrument_features = all_features[instrument].values
                    feature_vector.extend(instrument_features)
                else:
                    # If features not available, add zeros
                    logger.warning(f"Features not available for {instrument}, using zeros")
                    # Get size from another instrument
                    for other_instr, features in all_features.items():
                        zero_features = np.zeros(len(features))
                        feature_vector.extend(zero_features)
                        break
            
            # Convert to numpy array
            feature_vector = np.array(feature_vector)
            
            # Check if feature vector has the correct length for the model (1084)
            expected_length = 1084  # The expected number of features for the model
            actual_length = len(feature_vector)
            
            if actual_length != expected_length:
                logger.warning(f"Feature vector length mismatch: got {actual_length}, expected {expected_length}")
                
                if actual_length > expected_length:
                    # Truncate if too long
                    logger.info(f"Truncating feature vector from {actual_length} to {expected_length}")
                    feature_vector = feature_vector[:expected_length]
                else:
                    # Pad with zeros if too short
                    logger.info(f"Padding feature vector from {actual_length} to {expected_length}")
                    padding = np.zeros(expected_length - actual_length)
                    feature_vector = np.concatenate([feature_vector, padding])
            
            logger.info(f"Final feature vector shape: {feature_vector.shape}")
            return feature_vector
            
        except Exception as e:
            logger.error(f"Error preparing feature vector: {str(e)}")
            return None

def calculate_features(df: pd.DataFrame, instrument: str, **kwargs) -> pd.DataFrame:
    """
    Calculate features for a dataframe
    
    Args:
        df: DataFrame with OHLCV data
        instrument: The instrument name
        **kwargs: Additional parameters for feature calculation
        
    Returns:
        DataFrame with calculated features
    """
    # Ensure consistent column names
    expected_columns = ['open', 'high', 'low', 'close', 'volume']
    
    # Check if all expected columns exist (case-insensitive)
    df_columns_lower = [col.lower() for col in df.columns]
    for col in expected_columns:
        if col not in df_columns_lower:
            # Try to find a matching column case-insensitive
            for actual_col in df.columns:
                if actual_col.lower() == col:
                    # Rename the column to the expected lowercase name
                    df = df.rename(columns={actual_col: col})
                    break
    
    # Ensure all expected columns exist
    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(f"Missing column {col} in dataframe for {instrument}")
    
    # Get parameters for feature calculation
    price_features = kwargs.get('price_features', True)
    volume_features = kwargs.get('volume_features', True)
    
    ma_periods = kwargs.get('ma_periods', [3, 8, 13, 21, 34, 55, 89, 144])
    roc_periods = kwargs.get('roc_periods', [1, 2, 3, 5, 8, 13, 21, 34, 55, 89])
    std_periods = kwargs.get('std_periods', [3, 5, 8, 13, 21, 34, 55, 89])
    bb_periods = kwargs.get('bb_periods', [5, 13, 21, 34, 55])
    rsi_periods = kwargs.get('rsi_periods', [2, 3, 5, 8, 13, 21, 34])
    obv_periods = kwargs.get('obv_periods', [3, 5, 8, 13, 21, 34, 55, 89])
    
    # Create a new DataFrame for features
    features_df = pd.DataFrame(index=df.index)
    
    # Add price features
    if price_features:
        # Calculate moving averages
        for period in ma_periods:
            features_df[f'{instrument}_ma_{period}'] = df['close'].rolling(window=period).mean()
        
        # Calculate rate of change
        for period in roc_periods:
            features_df[f'{instrument}_roc_{period}'] = df['close'].pct_change(periods=period) * 100
        
        # Calculate standard deviation
        for period in std_periods:
            features_df[f'{instrument}_std_{period}'] = df['close'].rolling(window=period).std()
        
        # Calculate Bollinger Bands
        for period in bb_periods:
            mid = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = mid + 2 * std
            lower = mid - 2 * std
            features_df[f'{instrument}_bb_upper_{period}'] = upper
            features_df[f'{instrument}_bb_lower_{period}'] = lower
            features_df[f'{instrument}_bb_pct_{period}'] = (df['close'] - lower) / (upper - lower)
        
        # Calculate RSI
        for period in rsi_periods:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss.replace(0, 1e-10)  # Avoid division by zero
            rsi = 100 - (100 / (1 + rs))
            features_df[f'{instrument}_rsi_{period}'] = rsi
    
    # Add volume features
    if volume_features and 'volume' in df.columns:
        # Calculate OBV
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        features_df[f'{instrument}_obv'] = obv
        
        # Calculate OBV moving averages
        for period in obv_periods:
            features_df[f'{instrument}_obv_ma_{period}'] = obv.rolling(window=period).mean()
            
        # Calculate volume rate of change
        for period in roc_periods:
            features_df[f'{instrument}_vol_roc_{period}'] = df['volume'].pct_change(periods=period) * 100
            
        # Volume moving average
        for period in ma_periods:
            features_df[f'{instrument}_vol_ma_{period}'] = df['volume'].rolling(window=period).mean()
    
    # Fill NaN values that result from the moving window calculations
    features_df = features_df.fillna(method='bfill').fillna(0)
    
    return features_df

def main():
    """Simple test function to verify the module."""
    # Create data fetcher
    forex_instruments = PAIRS_BY_LIQUIDITY_OANDA[:5]  # Just use a few for testing
    etf_symbols = ["SPY", "QQQ", "IWM"]  # Example ETFs
    
    # Create data fetcher with both types
    data_fetcher = MarketDataFetcher(
        instruments=forex_instruments + etf_symbols,
        history_days=60,  # Just use 60 days for testing
        etf_symbols=etf_symbols
    )
    
    # Test fetching data for each type
    print("Testing fetch_price_data for forex:")
    forex_data = data_fetcher.fetch_price_data(forex_instruments[0])
    if forex_data is not None:
        print(f"{forex_instruments[0]} data shape: {forex_data.shape}")
        print(forex_data.head())
    
    print("\nTesting fetch_price_data for ETF:")
    etf_data = data_fetcher.fetch_price_data(etf_symbols[0])
    if etf_data is not None:
        print(f"{etf_symbols[0]} data shape: {etf_data.shape}")
        print(etf_data.head())
    
    # Test feature calculation
    print("\nTesting feature calculation:")
    for instrument in [forex_instruments[0], etf_symbols[0]]:
        features = data_fetcher.calculate_instrument_features(instrument)
        if features is not None:
            print(f"{instrument} features shape: {features.shape}")
            print(f"First 5 feature columns: {list(features.columns)[:5]}")
    
    # Test prepare_feature_vector
    print("\nTesting prepare_feature_vector:")
    feature_vector = data_fetcher.prepare_feature_vector()
    if feature_vector is not None:
        print(f"Feature vector shape: {feature_vector.shape}")

if __name__ == "__main__":
    main() 