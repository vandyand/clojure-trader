#!/usr/bin/env python3
"""
Test script for the data persistence layer.
"""
import sys
import os
from datetime import datetime, timedelta
import logging

# Add the workspace root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bitunix_rl.data.persistence import DataPersistence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_persistence():
    """Test the persistence layer functionality."""
    # Initialize persistence layer
    persistence = DataPersistence()
    
    # Test symbol
    symbol = "BTCUSDT"
    
    # Get data for the last 30 days
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    logger.info(f"Fetching data for {symbol} from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    
    # First fetch - should get from API
    candles = persistence.get_historical_data(
        symbol=symbol,
        interval="1d",
        start_time=start_time,
        end_time=end_time
    )
    
    logger.info(f"First fetch: {len(candles)} candles")
    
    # Get metadata
    metadata = persistence.get_symbol_metadata(symbol)
    if metadata:
        earliest = datetime.fromtimestamp(metadata['earliest_candle_time'] / 1000)
        latest = datetime.fromtimestamp(metadata['latest_candle_time'] / 1000)
        logger.info(f"Data range: {earliest.date()} to {latest.date()}")
    
    # Second fetch - should get from database
    logger.info("\nFetching again (should use cached data)...")
    candles2 = persistence.get_historical_data(
        symbol=symbol,
        interval="1d",
        start_time=start_time,
        end_time=end_time
    )
    
    logger.info(f"Second fetch: {len(candles2)} candles")
    
    # Verify data consistency
    if len(candles) == len(candles2):
        logger.info("Data consistency check passed")
    else:
        logger.error("Data consistency check failed")
    
    # Test fetching older data
    old_start_time = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
    logger.info(f"\nFetching older data from {datetime.fromtimestamp(old_start_time/1000)}")
    
    candles3 = persistence.get_historical_data(
        symbol=symbol,
        interval="1d",
        start_time=old_start_time,
        end_time=end_time
    )
    
    logger.info(f"Older data fetch: {len(candles3)} candles")
    
    # Get updated metadata
    metadata = persistence.get_symbol_metadata(symbol)
    if metadata:
        earliest = datetime.fromtimestamp(metadata['earliest_candle_time'] / 1000)
        latest = datetime.fromtimestamp(metadata['latest_candle_time'] / 1000)
        logger.info(f"Updated data range: {earliest.date()} to {latest.date()}")

if __name__ == "__main__":
    test_persistence() 