import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
import hashlib
import json
from diskcache import Cache

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from crypto_rl.constants import CRYPTO_PAIRS_BY_LIQUIDITY, ETF_SYMBOLS
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from api_clients.bitunix.bitunix.client import BitUnixClient
from crypto_rl.feature_engineering import calculate_features
from crypto_rl.data.fetch_etf_data import fetch_historical_etf_data, fetch_latest_etf_price

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"crypto_data_fetcher_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("crypto_data_fetcher")

class CryptoMarketDataFetcher:
    """
    Fetches and prepares market data for crypto and ETF instruments including:
    - Latest price data
    - Feature calculation
    
    Handles both CRYPTO (via Bitunix) and ETF (via yfinance) data sources.
    """
    
    def __init__(self, instruments: List[str] = None, 
                 feature_params: Dict[str, Any] = None, 
                 history_days: int = 3000,
                 crypto_pairs: List[str] = None,
                 etf_symbols: List[str] = None,
                 cache_dir: str = None,
                 cache_ttl: int = 3600):  # 1 hour default TTL
        """
        Initialize the data fetcher
        
        Args:
            instruments: List of instruments to fetch data for (default: CRYPTO_PAIRS_BY_LIQUIDITY + ETF_SYMBOLS)
            feature_params: Parameters for feature calculation
            history_days: Number of days of historical data to fetch
            crypto_pairs: Crypto pairs to include
            etf_symbols: ETF symbols to include
            cache_dir: Directory for disk cache (default: ./cache)
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self.crypto_pairs = crypto_pairs or CRYPTO_PAIRS_BY_LIQUIDITY
        self.etf_symbols = etf_symbols or ETF_SYMBOLS
        
        # Combine all instruments
        self.instruments = instruments or (self.crypto_pairs + self.etf_symbols)
        self.history_days = history_days
        self.cache_ttl = cache_ttl
        
        # Initialize disk cache
        cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        self.cache = Cache(cache_dir)
        logger.info(f"Initialized disk cache at: {cache_dir}")
        
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
            
        # Initialize Bitunix client
        self.bitunix_client = BitUnixClient()
        
        # Cache for price data and features
        self.price_data_cache = {}
        self.feature_cache = {}
        self.last_update_time = {}
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a unique cache key based on parameters
        
        Args:
            prefix: Cache key prefix
            **kwargs: Parameters to include in cache key
            
        Returns:
            Unique cache key string
        """
        # Sort kwargs to ensure consistent key generation
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        
        # Create hash of parameters
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        
        return f"{prefix}_{param_hash}"
    
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """
        Get data from cache
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            if cache_key in self.cache:
                logger.debug(f"Cache hit for key: {cache_key}")
                return self.cache[cache_key]
            else:
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
        except Exception as e:
            logger.warning(f"Error accessing cache for key {cache_key}: {e}")
            return None
    
    def _set_cached_data(self, cache_key: str, data: Any) -> None:
        """
        Store data in cache with TTL
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        try:
            self.cache.set(cache_key, data, expire=self.cache_ttl)
            logger.debug(f"Cached data for key: {cache_key}")
        except Exception as e:
            logger.warning(f"Error caching data for key {cache_key}: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        try:
            self.cache.clear()
            logger.info("Cleared all cached data")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            return {
                'cache_dir': self.cache.directory,
                'cache_size': len(self.cache),
                'cache_volume': self.cache.volume(),
                'cache_hits': getattr(self.cache, 'hits', 0),
                'cache_misses': getattr(self.cache, 'misses', 0)
            }
        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {}
    
    def is_crypto(self, instrument: str) -> bool:
        """
        Determine if an instrument is a crypto pair or ETF.
        
        Args:
            instrument: The instrument to check
            
        Returns:
            True if crypto (Bitunix), False if ETF/stock
        """
        return instrument in self.crypto_pairs
        
    def fetch_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch price data for the specified instrument from the appropriate source
        
        Args:
            instrument: The instrument to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        if self.is_crypto(instrument):
            return self._fetch_crypto_price_data(instrument)
        else:
            return self._fetch_etf_price_data(instrument)
    
    def _fetch_crypto_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch crypto price data from Bitunix in chunks to handle large datasets
        
        Args:
            instrument: The crypto instrument to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        # Generate cache key for this request
        cache_key = self._generate_cache_key(
            "crypto_data",
            instrument=instrument,
            history_days=self.history_days
        )
        
        # Try to get from cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"Using cached data for {instrument} ({len(cached_data)} candles)")
            return cached_data
        
        try:
            # Calculate start date for historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.history_days)
            
            # Convert to milliseconds timestamp
            start_time = int(start_date.timestamp() * 1000)
            end_time = int(end_date.timestamp() * 1000)
            
            logger.info(f"Fetching {self.history_days} days of data for {instrument} from {start_date.date()} to {end_date.date()}")
            
            all_candles = []
            current_end = end_time
            chunk_count = 0
            
            # Fetch data in chunks (Bitunix API limit is 200-500 candles per request)
            while current_end > start_time:
                chunk_count += 1
                
                # Calculate a time window for this chunk (about 400 days worth of daily candles)
                window_start = max(start_time, current_end - (400 * 24 * 60 * 60 * 1000))
                
                logger.info(f"Fetching chunk {chunk_count} for {instrument} (end_time: {datetime.fromtimestamp(current_end/1000).date()})")
                
                # Fetch a chunk of candles
                chunk = self.bitunix_client.get_historical_klines(
                    symbol=instrument,
                    interval="1d",  # Daily data
                    start_time=window_start,
                    end_time=current_end,
                    limit=399  # Maximum allowed by API
                )
                
                if not chunk:
                    logger.info(f"No data available for {instrument} in this time window")
                    # Move back by a smaller amount if no data
                    current_end = window_start - 1
                    continue
                    
                all_candles.extend(chunk)
                logger.info(f"Fetched {len(chunk)} candles in chunk {chunk_count}")
                
                # Update end time for next chunk (go back in time)
                # Use the earliest candle's open_time as the new end time
                earliest_time = min(c.open_time for c in chunk)
                if earliest_time >= current_end:  # No more data available
                    logger.info(f"Reached earliest available data for {instrument}")
                    break
                    
                current_end = earliest_time - 1  # Subtract 1ms to avoid overlap
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.1)
            
            if not all_candles:
                logger.warning(f"No candles returned for {instrument}")
                return None
                
            # Parse candles into DataFrame
            data = []
            for candle in all_candles:
                timestamp = pd.to_datetime(candle.open_time, unit='ms')
                
                row = {
                    "time": timestamp,
                    "open": float(candle.open_price),
                    "high": float(candle.high_price),
                    "low": float(candle.low_price),
                    "close": float(candle.close_price),
                    "volume": float(candle.volume),
                }
                data.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(data)
            df.set_index("time", inplace=True)
            df.sort_index(inplace=True)
            
            # Remove duplicates if any
            df = df[~df.index.duplicated(keep='first')]
            
            # Store in cache
            self._set_cached_data(cache_key, df)
            self.price_data_cache[instrument] = df
            self.last_update_time[instrument] = datetime.now()
            
            logger.info(f"Fetched {len(df)} candles for {instrument} (from {df.index.min().date()} to {df.index.max().date()})")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching crypto data for {instrument}: {e}")
            return None
    
    def _fetch_etf_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch ETF price data from yfinance
        
        Args:
            instrument: The ETF instrument to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        # Generate cache key for this request
        cache_key = self._generate_cache_key(
            "etf_data",
            instrument=instrument,
            history_days=self.history_days
        )
        
        # Try to get from cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"Using cached data for {instrument} ({len(cached_data)} candles)")
            return cached_data
        
        try:
            # Calculate start date for historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.history_days)
            
            # Fetch data from yfinance
            df = fetch_historical_etf_data(
                symbol=instrument,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {instrument}")
                return None
            
            # Ensure column names match expected format
            if 'Open' in df.columns:
                df = df.rename(columns={
                    'Open': 'open',
                    'High': 'high', 
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
            
            # Store in cache
            self._set_cached_data(cache_key, df)
            self.price_data_cache[instrument] = df
            self.last_update_time[instrument] = datetime.now()
            
            logger.info(f"Fetched {len(df)} candles for {instrument}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching ETF data for {instrument}: {e}")
            return None
    
    def calculate_instrument_features(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Calculate features for a specific instrument
        
        Args:
            instrument: The instrument to calculate features for
            
        Returns:
            DataFrame with calculated features or None if error
        """
        try:
            # Get price data
            price_data = self.fetch_price_data(instrument)
            if price_data is None:
                return None
            
            # Calculate features
            features = calculate_features(price_data, instrument, **self.feature_params)
            
            # Store in cache
            self.feature_cache[instrument] = features
            self.last_update_time[f"{instrument}_features"] = datetime.now()
            
            return features
            
        except Exception as e:
            logger.error(f"Error calculating features for {instrument}: {e}")
            return None
    
    def get_latest_features(self, instrument: str, recalculate: bool = False) -> Optional[pd.Series]:
        """
        Get the latest features for a specific instrument
        
        Args:
            instrument: The instrument to get features for
            recalculate: Whether to recalculate features even if cached
            
        Returns:
            Series with latest features or None if error
        """
        try:
            # Check cache first
            if not recalculate and instrument in self.feature_cache:
                features_df = self.feature_cache[instrument]
                if not features_df.empty:
                    return features_df.iloc[-1]
            
            # Calculate features
            features_df = self.calculate_instrument_features(instrument)
            if features_df is None or features_df.empty:
                return None
            
            return features_df.iloc[-1]
            
        except Exception as e:
            logger.error(f"Error getting latest features for {instrument}: {e}")
            return None
    
    def get_all_latest_features(self, recalculate: bool = False) -> Dict[str, pd.Series]:
        """
        Get the latest features for all instruments
        
        Args:
            recalculate: Whether to recalculate features even if cached
            
        Returns:
            Dictionary mapping instruments to their latest features
        """
        all_features = {}
        
        for instrument in self.instruments:
            features = self.get_latest_features(instrument, recalculate)
            if features is not None:
                all_features[instrument] = features
        
        return all_features
    
    def get_latest_price_for_instrument(self, instrument: str) -> Optional[float]:
        """
        Get the latest price for a specific instrument
        
        Args:
            instrument: The instrument to get price for
            
        Returns:
            Latest price or None if error
        """
        # Generate cache key for latest price request
        cache_key = self._generate_cache_key(
            "latest_price",
            instrument=instrument
        )
        
        # Try to get from cache first (shorter TTL for latest prices)
        cached_price = self._get_cached_data(cache_key)
        if cached_price is not None:
            logger.debug(f"Using cached latest price for {instrument}: {cached_price}")
            return cached_price
        
        try:
            if self.is_crypto(instrument):
                # For crypto, get from Bitunix
                candles = self.bitunix_client.get_historical_klines(
                    symbol=instrument,
                    interval="1d",
                    limit=1
                )
                if candles:
                    latest_price = float(candles[0].close_price)
                    # Cache with shorter TTL (5 minutes) for latest prices
                    self.cache.set(cache_key, latest_price, expire=300)
                    return latest_price
            else:
                # For ETFs, get from yfinance
                latest_price = fetch_latest_etf_price(instrument)
                if latest_price is not None:
                    # Cache with shorter TTL (5 minutes) for latest prices
                    self.cache.set(cache_key, latest_price, expire=300)
                    return latest_price
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest price for {instrument}: {e}")
            return None
    
    def prepare_feature_vector(self) -> Optional[np.ndarray]:
        """
        Prepare a feature vector for all instruments
        
        Returns:
            Numpy array with all features or None if error
        """
        try:
            # Get all latest features
            all_features = self.get_all_latest_features()
            
            if not all_features:
                logger.error("No features available for any instrument")
                return None
            
            # Combine all features into a single vector
            feature_vectors = []
            feature_names = []
            
            for instrument, features in all_features.items():
                # Add instrument prefix to feature names
                for feature_name, value in features.items():
                    if not pd.isna(value) and not np.isinf(value):
                        feature_vectors.append(value)
                        feature_names.append(f"{instrument}__{feature_name}")
            
            if not feature_vectors:
                logger.error("No valid features found")
                return None
            
            # Convert to numpy array
            feature_vector = np.array(feature_vectors, dtype=np.float32)
            
            logger.info(f"Prepared feature vector with {len(feature_vector)} features")
            return feature_vector
            
        except Exception as e:
            logger.error(f"Error preparing feature vector: {e}")
            return None

def calculate_features(df: pd.DataFrame, instrument: str, **kwargs) -> pd.DataFrame:
    """
    Calculate features for a price DataFrame
    
    Args:
        df: DataFrame with price data
        instrument: Instrument name
        **kwargs: Feature parameters
        
    Returns:
        DataFrame with calculated features
    """
    # Collect all features in a dictionary to avoid DataFrame fragmentation
    feature_dict = {}
    
    # Price-based features
    if kwargs.get('price_features', True):
        # Simple returns
        feature_dict[f"{instrument}__close_return"] = df["close"].pct_change()
        
        # Log returns
        feature_dict[f"{instrument}__close_log_return"] = np.log(df["close"] / df["close"].shift(1))
        
        # Price range
        feature_dict[f"{instrument}__high_low_range"] = (df["high"] - df["low"]) / df["close"]
        
        # Moving averages
        for period in kwargs.get('ma_periods', [3, 8, 21, 55, 144]):
            feature_dict[f"{instrument}__close_sma_{period}"] = df["close"].rolling(window=period).mean()
            feature_dict[f"{instrument}__close_ema_{period}"] = df["close"].ewm(span=period).mean()
        
        # Rate of change
        for period in kwargs.get('roc_periods', [1, 3, 8, 21, 55]):
            feature_dict[f"{instrument}__close_roc_{period}"] = df["close"].pct_change(periods=period)
        
        # Standard deviation
        for period in kwargs.get('std_periods', [5, 13, 21, 55]):
            feature_dict[f"{instrument}__close_std_{period}"] = df["close"].rolling(window=period).std()
        
        # Bollinger Bands
        for period in kwargs.get('bb_periods', [20]):
            mid = df["close"].rolling(window=period).mean()
            std = df["close"].rolling(window=period).std()
            feature_dict[f"{instrument}__close_bb_mid_{period}"] = mid
            feature_dict[f"{instrument}__close_bb_bbhi_{period}"] = (df["close"] - (mid + 2 * std)) / df["close"]
            feature_dict[f"{instrument}__close_bb_bblo_{period}"] = (df["close"] - (mid - 2 * std)) / df["close"]
        
        # RSI
        for period in kwargs.get('rsi_periods', [2, 8, 14]):
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss
            feature_dict[f"{instrument}__close_rsi_{period}"] = 100 - (100 / (1 + rs))
    
    # Volume-based features
    if 'volume' in df.columns and kwargs.get('volume_features', True):
        # Moving averages
        for period in kwargs.get('ma_periods', [3, 8, 21, 55, 144]):
            feature_dict[f"{instrument}__volume_sma_{period}"] = df["volume"].rolling(window=period).mean()
        
        # Rate of change
        for period in kwargs.get('roc_periods', [1, 3, 8, 21, 55]):
            feature_dict[f"{instrument}__volume_roc_{period}"] = df["volume"].pct_change(periods=period)
        
        # Standard deviation
        for period in kwargs.get('std_periods', [5, 13, 21, 55]):
            feature_dict[f"{instrument}__volume_std_{period}"] = df["volume"].rolling(window=period).std()
        
        # Volume max/min
        for period in kwargs.get('ma_periods', [5, 13, 21, 55]):
            feature_dict[f"{instrument}__volume_roll_max_{period}"] = df["volume"].rolling(window=period).max() / df["volume"]
            feature_dict[f"{instrument}__volume_roll_min_{period}"] = df["volume"].rolling(window=period).min() / df["volume"]
        
        # Bollinger Bands for volume
        for period in kwargs.get('bb_periods', [20]):
            mid = df["volume"].rolling(window=period).mean()
            std = df["volume"].rolling(window=period).std()
            feature_dict[f"{instrument}__volume_bb_mid_{period}"] = mid
            feature_dict[f"{instrument}__volume_bb_bbh_{period}"] = (df["volume"] - (mid + 2 * std)) / df["volume"]
            feature_dict[f"{instrument}__volume_bb_bbl_{period}"] = (df["volume"] - (mid - 2 * std)) / df["volume"]
        
        # On-Balance Volume
        obv = (df["volume"] * ((df["close"] > df["close"].shift(1)).astype(int) - 
                              (df["close"] < df["close"].shift(1)).astype(int))).cumsum()
        feature_dict[f"{instrument}__volume_obv"] = obv
        
        # OBV moving averages
        for period in kwargs.get('obv_periods', [3, 8, 21]):
            feature_dict[f"{instrument}__volume_obv_{period}"] = obv.rolling(window=period).mean()
    
    # Create DataFrame from all features at once to avoid fragmentation
    features = pd.DataFrame(feature_dict, index=df.index)
    
    # Clean up any infinite or NaN values
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.fillna(0)
    
    return features

def main():
    """Test the data fetcher"""
    fetcher = CryptoMarketDataFetcher()
    
    # Test with a few instruments
    test_instruments = ["BTCUSDT", "ETHUSDT", "SPY", "QQQ"]
    
    for instrument in test_instruments:
        print(f"\nTesting {instrument}...")
        
        # Get price data
        price_data = fetcher.fetch_price_data(instrument)
        if price_data is not None:
            print(f"  Price data shape: {price_data.shape}")
            print(f"  Latest close: {price_data['close'].iloc[-1]:.4f}")
        
        # Get features
        features = fetcher.calculate_instrument_features(instrument)
        if features is not None:
            print(f"  Features shape: {features.shape}")
            print(f"  Number of features: {len(features.columns)}")
    
    # Test feature vector preparation
    print("\nPreparing feature vector...")
    feature_vector = fetcher.prepare_feature_vector()
    if feature_vector is not None:
        print(f"Feature vector shape: {feature_vector.shape}")
        print(f"Feature vector sample: {feature_vector[:10]}")

if __name__ == "__main__":
    main() 