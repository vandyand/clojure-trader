#!/usr/bin/env python3
"""
Script to collect historical daily candlestick data for BTCUSDT.
Note: Bitunix API has a hard limit of 399 daily candles per request.
"""
import sys
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Add the workspace root to the Python path so both bitunix and bitunix_rl are importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bitunix.client import BitUnixClient
from bitunix.models import Candlestick
from bitunix_rl.data.persistence import DataPersistence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Focus on BTCUSDT only
TRADING_PAIRS = ["BTCUSDT"]

def collect_historical_data(
    symbols: List[str],
    interval: str = "1d",
    days_back: int = 3000
) -> Dict[str, List[Candlestick]]:
    """
    Collect historical candlestick data for the given symbols using the persistence layer.
    
    Args:
        symbols: List of trading pair symbols
        interval: Time interval for candlesticks (e.g., '1d')
        days_back: Number of days of historical data to fetch
    
    Returns:
        Dictionary mapping symbols to lists of Candlestick objects
    """
    persistence = DataPersistence()
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
    
    logger.info(f"Fetching {days_back} days of historical data from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    
    all_data = {}
    for symbol in symbols:
        logger.info(f"Fetching data for {symbol}...")
        try:
            # Get data from persistence layer (will fetch from API if needed)
            candles = persistence.get_historical_data(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            all_data[symbol] = candles
            
            # Get metadata for logging
            metadata = persistence.get_symbol_metadata(symbol)
            if metadata:
                earliest = datetime.fromtimestamp(metadata['earliest_candle_time'] / 1000)
                latest = datetime.fromtimestamp(metadata['latest_candle_time'] / 1000)
                logger.info(
                    f"Fetched {len(candles)} daily candles for {symbol} "
                    f"(from {earliest.date()} to {latest.date()})"
                )
            else:
                logger.info(f"Fetched {len(candles)} daily candles for {symbol}")
                
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            continue
    
    return all_data

def save_to_csv(data: Dict[str, List[Candlestick]], output_dir: str = "data"):
    """
    Save the collected data to CSV files.
    
    Args:
        data: Dictionary mapping symbols to lists of Candlestick objects
        output_dir: Directory to save CSV files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for symbol, candles in data.items():
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'timestamp': pd.to_datetime(c.open_time, unit='ms'),
                'open': c.open_price,
                'high': c.high_price,
                'low': c.low_price,
                'close': c.close_price,
                'volume': c.volume,
                'quote_volume': c.quote_volume
            }
            for c in candles
        ])
        
        # Set timestamp as index and sort
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Save to CSV
        output_file = os.path.join(output_dir, f"{symbol}_daily.csv")
        df.to_csv(output_file)
        logger.info(f"Saved {len(df)} candles to {output_file}")

if __name__ == "__main__":
    logger.info(f"Starting data collection for {len(TRADING_PAIRS)} trading pairs...")
    logger.info("Note: Bitunix API has a hard limit of 399 daily candles per request.")
    
    historical_data = collect_historical_data(TRADING_PAIRS)
    
    # Print summary
    logger.info("\nData Collection Summary:")
    for symbol, candles in historical_data.items():
        logger.info(f"{symbol}: {len(candles)} candles")
    
    # Save to CSV files
    logger.info("\nSaving data to CSV files...")
    save_to_csv(historical_data) 