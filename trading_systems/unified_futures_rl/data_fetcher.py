"""
Real Data Fetcher for Unified Futures RL Trading System

Fetches real market data from:
- Bitunix API for crypto perpetual futures data
- yfinance for ETF data

Based on the working crypto_rl implementation with caching and error handling.
"""

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
import yfinance as yf

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from constants import CRYPTO_FUTURES_PAIRS, ETF_SYMBOLS

# Add path for Bitunix client
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from api_clients.bitunix.bitunix.client import BitUnixClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"unified_futures_data_fetcher_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("unified_futures_data_fetcher")

class UnifiedFuturesDataFetcher:
    """
    Fetches and prepares real market data for crypto futures and ETF instruments.
    
    Features:
    - Real-time data from Bitunix API for crypto futures
    - ETF data from yfinance
    - Intelligent caching with TTL
    - Error handling and retry logic
    - Data validation and cleaning
    """
    
    def __init__(self, 
                 crypto_pairs: List[str] = None,
                 etf_symbols: List[str] = None,
                 history_days: int = 1500,  # Increased to ensure 1000+ candles
                 cache_dir: str = None,
                 cache_ttl: int = 3600):  # 1 hour default TTL
        """
        Initialize the data fetcher
        
        Args:
            crypto_pairs: List of crypto futures pairs to fetch
            etf_symbols: List of ETF symbols to fetch
            history_days: Number of days of historical data to fetch
            cache_dir: Directory for disk cache
            cache_ttl: Cache TTL in seconds
        """
        self.crypto_pairs = crypto_pairs or CRYPTO_FUTURES_PAIRS
        self.etf_symbols = etf_symbols or ETF_SYMBOLS
        self.history_days = history_days
        self.cache_ttl = cache_ttl
        
        # Initialize disk cache
        cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        self.cache = Cache(cache_dir)
        logger.info(f"Initialized disk cache at: {cache_dir}")
        
        # Initialize Bitunix client
        self.bitunix_client = BitUnixClient()
        
        # Cache for price data
        self.price_data_cache = {}
        self.last_update_time = {}
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters."""
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        key_string = f"{prefix}_{sorted_kwargs}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if not expired and has sufficient data."""
        try:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                # Check if cache is still valid
                cache_time = self.cache.touch(cache_key)
                if cache_time is not None and isinstance(cache_time, datetime):
                    if (datetime.now() - cache_time).seconds < self.cache_ttl:
                        # Additional validation: check if cached data has enough candles
                        if hasattr(cached_data, '__len__') and len(cached_data) >= 1000:
                            return cached_data
                        else:
                            # Cached data doesn't have enough candles, remove it
                            logger.info(f"Cached data for {cache_key} has insufficient candles ({len(cached_data)}), fetching fresh data")
                            self.cache.delete(cache_key)
                    else:
                        # Cache expired, remove it
                        self.cache.delete(cache_key)
                else:
                    # Invalid cache time, check data quality anyway
                    if hasattr(cached_data, '__len__') and len(cached_data) >= 1000:
                        return cached_data
                    else:
                        logger.info(f"Cached data for {cache_key} has insufficient candles ({len(cached_data)}), fetching fresh data")
                        self.cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"Error accessing cache: {e}")
        return None
    
    def _set_cached_data(self, cache_key: str, data: Any) -> None:
        """Store data in cache."""
        try:
            self.cache.set(cache_key, data, expire=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Error storing in cache: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            self.cache.clear()
            self.price_data_cache.clear()
            self.last_update_time.clear()
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            return {
                'cache_size': len(self.cache),
                'cache_dir': self.cache.directory,
                'price_cache_size': len(self.price_data_cache),
                'last_updates': self.last_update_time
            }
        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {}
    
    def is_crypto(self, instrument: str) -> bool:
        """Check if instrument is a crypto futures pair."""
        return instrument in self.crypto_pairs
    
    def fetch_price_data(self, instrument: str) -> Optional[pd.DataFrame]:
        """
        Fetch price data for an instrument.
        
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
        Fetch crypto futures price data from Bitunix API.
        
        Args:
            instrument: The crypto futures instrument to fetch data for
            
        Returns:
            DataFrame with price data or None if error
        """
        # Generate cache key for this request
        cache_key = self._generate_cache_key(
            "crypto_futures_data",
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
                
                # Calculate a time window for this chunk (about 500 days worth of daily candles)
                window_start = max(start_time, current_end - (500 * 24 * 60 * 60 * 1000))
                
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
        Fetch ETF price data from yfinance.
        
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
            
            logger.info(f"Fetching {self.history_days} days of ETF data for {instrument}")
            
            # Fetch data from yfinance
            ticker = yf.Ticker(instrument)
            df = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if df.empty:
                logger.warning(f"No data returned for ETF {instrument}")
                return None
            
            # Convert timezone-aware index to timezone-naive for consistency
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # Rename columns to match our expected format
            df.columns = [col.lower() for col in df.columns]
            
            # Ensure we have the required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} for {instrument}")
                    return None
            
            # Store in cache
            self._set_cached_data(cache_key, df)
            self.price_data_cache[instrument] = df
            self.last_update_time[instrument] = datetime.now()
            
            logger.info(f"Fetched {len(df)} candles for ETF {instrument} (from {df.index.min().date()} to {df.index.max().date()})")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching ETF data for {instrument}: {e}")
            return None
    
    def fetch_all_crypto_data(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all crypto futures pairs.
        
        Returns:
            Dictionary mapping instrument names to DataFrames
        """
        crypto_data = {}
        
        for pair in self.crypto_pairs:
            logger.info(f"Fetching data for crypto futures pair: {pair}")
            data = self.fetch_price_data(pair)
            if data is not None:
                crypto_data[pair] = data
            else:
                logger.warning(f"Failed to fetch data for {pair}")
        
        logger.info(f"Successfully fetched data for {len(crypto_data)}/{len(self.crypto_pairs)} crypto pairs")
        return crypto_data
    
    def fetch_all_etf_data(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all ETF symbols.
        
        Returns:
            Dictionary mapping ETF symbols to DataFrames
        """
        etf_data = {}
        
        for symbol in self.etf_symbols:
            logger.info(f"Fetching data for ETF: {symbol}")
            data = self.fetch_price_data(symbol)
            if data is not None:
                etf_data[symbol] = data
            else:
                logger.warning(f"Failed to fetch data for {symbol}")
        
        logger.info(f"Successfully fetched data for {len(etf_data)}/{len(self.etf_symbols)} ETFs")
        return etf_data
    
    def fetch_all_data(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Fetch data for all instruments.
        
        Returns:
            Dictionary with 'crypto' and 'etf' keys containing respective data
        """
        logger.info("Fetching all market data...")
        
        crypto_data = self.fetch_all_crypto_data()
        etf_data = self.fetch_all_etf_data()
        
        return {
            'crypto': crypto_data,
            'etf': etf_data
        }
    
    def get_latest_prices(self) -> Dict[str, float]:
        """
        Get latest prices for all instruments.
        
        Returns:
            Dictionary mapping instrument names to latest close prices
        """
        latest_prices = {}
        
        # Get latest crypto prices
        for pair in self.crypto_pairs:
            if pair in self.price_data_cache and not self.price_data_cache[pair].empty:
                latest_prices[pair] = self.price_data_cache[pair]['close'].iloc[-1]
        
        # Get latest ETF prices
        for symbol in self.etf_symbols:
            if symbol in self.price_data_cache and not self.price_data_cache[symbol].empty:
                latest_prices[symbol] = self.price_data_cache[symbol]['close'].iloc[-1]
        
        return latest_prices
    
    def validate_data_quality(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Validate the quality of fetched data.
        
        Args:
            data: Dictionary of DataFrames
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {}
        
        for instrument, df in data.items():
            if df is None or df.empty:
                validation_results[instrument] = {
                    'valid': False,
                    'reason': 'No data available'
                }
                continue
            
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_results[instrument] = {
                    'valid': False,
                    'reason': f'Missing columns: {missing_columns}'
                }
                continue
            
            # Check for NaN values
            nan_counts = df[required_columns].isna().sum()
            total_rows = len(df)
            
            # Check data recency
            latest_date = df.index.max()
            # Handle timezone-aware vs timezone-naive datetime comparison
            if latest_date.tz is not None:
                # Convert timezone-aware to naive for comparison
                latest_date = latest_date.tz_localize(None)
            days_old = (datetime.now() - latest_date).days
            
            validation_results[instrument] = {
                'valid': True,
                'total_rows': total_rows,
                'date_range': f"{df.index.min().date()} to {df.index.max().date()}",
                'days_old': days_old,
                'nan_counts': nan_counts.to_dict(),
                'latest_price': df['close'].iloc[-1]
            }
        
        return validation_results

def main():
    """Test the data fetcher."""
    # Initialize fetcher
    fetcher = UnifiedFuturesDataFetcher(history_days=100)
    
    # Fetch all data
    all_data = fetcher.fetch_all_data()
    
    # Validate data quality
    crypto_validation = fetcher.validate_data_quality(all_data['crypto'])
    etf_validation = fetcher.validate_data_quality(all_data['etf'])
    
    # Print results
    print("\n=== Crypto Futures Data ===")
    for pair, result in crypto_validation.items():
        if result['valid']:
            print(f"{pair}: {result['total_rows']} rows, latest: {result['latest_price']:.4f}")
        else:
            print(f"{pair}: {result['reason']}")
    
    print("\n=== ETF Data ===")
    for symbol, result in etf_validation.items():
        if result['valid']:
            print(f"{symbol}: {result['total_rows']} rows, latest: {result['latest_price']:.4f}")
        else:
            print(f"{symbol}: {result['reason']}")
    
    # Print cache stats
    cache_stats = fetcher.get_cache_stats()
    print(f"\n=== Cache Stats ===")
    print(f"Cache size: {cache_stats.get('cache_size', 0)}")
    print(f"Price cache size: {cache_stats.get('price_cache_size', 0)}")

if __name__ == "__main__":
    main() 