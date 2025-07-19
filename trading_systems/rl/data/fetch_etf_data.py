#!/usr/bin/env python
import os
import sys
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import time
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("etf_data_fetcher")

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_TTL = 24 * 60 * 60  # 24 hours in seconds

def ensure_cache_dir():
    """Ensure the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_file_path(ticker: str, period: str) -> str:
    """Generate a cache file path for a given ticker and period."""
    return os.path.join(CACHE_DIR, f"{ticker}_{period}.json")

def cache_data(ticker: str, period: str, data: pd.DataFrame):
    """Cache dataframe to a file."""
    ensure_cache_dir()
    cache_file = get_cache_file_path(ticker, period)
    
    # Convert data to a serializable format
    data_dict = {
        "timestamp": datetime.now().timestamp(),
        "columns": list(data.columns),
        "index": [idx.strftime("%Y-%m-%d %H:%M:%S") if hasattr(idx, 'strftime') else str(idx) for idx in data.index],
        "data": data.values.tolist()
    }
    
    with open(cache_file, 'w') as f:
        json.dump(data_dict, f)
    
    logger.info(f"Cached data for {ticker} ({period}) to {cache_file}")

def get_cached_data(ticker: str, period: str) -> Optional[pd.DataFrame]:
    """Get data from cache if not expired."""
    cache_file = get_cache_file_path(ticker, period)
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            data_dict = json.load(f)
        
        # Check if cache is expired
        cache_time = data_dict["timestamp"]
        if (datetime.now().timestamp() - cache_time) > CACHE_TTL:
            logger.info(f"Cache expired for {ticker} ({period})")
            return None
        
        # Reconstruct DataFrame
        index = pd.to_datetime(data_dict["index"])
        df = pd.DataFrame(data_dict["data"], index=index, columns=data_dict["columns"])
        logger.info(f"Loaded cached data for {ticker} ({period})")
        return df
        
    except Exception as e:
        logger.warning(f"Error reading cache for {ticker}: {e}")
        return None

def fetch_historical_etf_data(ticker: str, period: str = "1y", interval: str = "1d", 
                            use_cache: bool = True, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    Fetch historical ETF data using yfinance.
    
    Args:
        ticker: ETF ticker symbol (e.g., "SPY")
        period: Time period to fetch (e.g., "1d", "5d", "1mo", "3mo", "1y", "5y", "max")
        interval: Data interval (e.g., "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
        use_cache: Whether to use cache if available
        max_retries: Maximum number of retry attempts for network issues
        
    Returns:
        DataFrame with historical OHLCV data or None if error
    """
    if use_cache:
        cached_data = get_cached_data(ticker, period)
        if cached_data is not None:
            logger.info(f"Using cached data for {ticker}")
            return cached_data
    
    # Initialize retry counter
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            logger.info(f"Fetching historical data for {ticker} (period: {period}, interval: {interval}) - attempt {retry_count + 1}")
            
            # Create ticker object
            etf = yf.Ticker(ticker)
            
            # Fetch historical data
            df = etf.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                retry_count += 1
                time.sleep(1)  # Brief pause before retry
                continue
            
            # Check for minimal data requirements
            if len(df) < 5:
                logger.warning(f"Insufficient data for {ticker}: only {len(df)} rows")
                retry_count += 1
                time.sleep(1)
                continue
            
            # Ensure DataFrame has expected columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                logger.warning(f"Missing columns for {ticker}: {missing}. Available: {df.columns}")
                
                # If missing just Volume, we can still work with it
                if missing == ['Volume'] and 'Close' in df.columns:
                    logger.info(f"Creating empty Volume column for {ticker}")
                    df['Volume'] = 0
                else:
                    retry_count += 1
                    time.sleep(1)
                    continue
            
            # Standardize column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Check for too many NaN values
            nan_pcts = df[['open', 'high', 'low', 'close']].isna().mean()
            if (nan_pcts > 0.3).any():
                logger.warning(f"Too many NaN values in data for {ticker}: {nan_pcts.to_dict()}")
                retry_count += 1
                time.sleep(1)
                continue
            
            # Handle any NaN values with forward-fill then backward-fill method
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # If still have NaNs, fill with zeros as last resort
            if df[['open', 'high', 'low', 'close']].isna().any().any():
                logger.warning(f"Still have NaN values after ffill/bfill for {ticker} - filling with zeros")
                df = df.fillna(0)
            
            # Cache the data if requested
            if use_cache:
                cache_data(ticker, period, df)
            
            logger.info(f"Successfully fetched {len(df)} records for {ticker}")
            return df
            
        except Exception as e:
            last_error = e
            logger.warning(f"Error fetching data for {ticker} (attempt {retry_count + 1}): {e}")
            retry_count += 1
            time.sleep(2)  # Slightly longer pause after an error
    
    # If we've exhausted retries
    logger.error(f"Failed to fetch data for {ticker} after {max_retries} attempts. Last error: {last_error}")
    return None

def fetch_latest_etf_price(ticker: str) -> Optional[float]:
    """
    Fetch latest price for an ETF.
    
    Args:
        ticker: ETF ticker symbol
        
    Returns:
        Latest price or None if error
    """
    try:
        logger.info(f"Fetching latest price for {ticker}")
        
        # Create ticker object
        etf = yf.Ticker(ticker)
        
        # Get latest price information
        price_info = etf.info
        
        if 'regularMarketPrice' in price_info:
            price = price_info['regularMarketPrice']
            logger.info(f"Latest price for {ticker}: {price}")
            return price
        else:
            logger.warning(f"No price information found for {ticker}")
            
            # Try getting from history as fallback
            df = etf.history(period="1d")
            if not df.empty and 'Close' in df.columns:
                price = df['Close'].iloc[-1]
                logger.info(f"Latest price for {ticker} (from history): {price}")
                return price
            
            return None
        
    except Exception as e:
        logger.error(f"Error fetching latest price for {ticker}: {e}")
        return None

def fetch_multiple_etfs(tickers: List[str], period: str = "1y", interval: str = "1d",
                       use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple ETF tickers.
    
    Args:
        tickers: List of ETF ticker symbols
        period: Time period to fetch
        interval: Data interval
        use_cache: Whether to use cache
        
    Returns:
        Dictionary of ticker -> DataFrame with historical data
    """
    results = {}
    
    for ticker in tickers:
        try:
            df = fetch_historical_etf_data(ticker, period, interval, use_cache)
            if df is not None:
                results[ticker] = df
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
    
    logger.info(f"Fetched data for {len(results)}/{len(tickers)} ETFs")
    return results

def fetch_etf_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch information about an ETF including description, sector, holdings, etc.
    
    Args:
        ticker: ETF ticker symbol
        
    Returns:
        Dictionary with ETF information or None if error
    """
    try:
        logger.info(f"Fetching information for {ticker}")
        
        # Create ticker object
        etf = yf.Ticker(ticker)
        
        # Get information
        info = etf.info
        
        return info
        
    except Exception as e:
        logger.error(f"Error fetching information for {ticker}: {e}")
        return None

def main():
    """Simple test function to verify the module."""
    # Example ETFs to test
    test_etfs = ["SPY", "QQQ", "IWM", "GLD", "VIX"]
    
    # Test individual fetch
    print("Testing individual ETF fetch:")
    spy_data = fetch_historical_etf_data("SPY", period="1mo")
    if spy_data is not None:
        print(f"SPY data shape: {spy_data.shape}")
        print(spy_data.head())
    
    # Test latest price
    print("\nTesting latest price fetch:")
    for etf in test_etfs[:2]:  # Just test first two
        price = fetch_latest_etf_price(etf)
        print(f"{etf} latest price: {price}")
    
    # Test multiple fetch
    print("\nTesting multiple ETF fetch:")
    multi_data = fetch_multiple_etfs(test_etfs, period="5d")
    for ticker, data in multi_data.items():
        print(f"{ticker} data shape: {data.shape}")

if __name__ == "__main__":
    main() 