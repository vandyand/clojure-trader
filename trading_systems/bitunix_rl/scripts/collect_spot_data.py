"""
Script to collect historical spot market data for training the RL model.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from bitunix_rl.data.spot_persistence import SpotDataPersistence
from bitunix.models import Candlestick

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def collect_spot_historical_data(
    symbols: List[str],
    interval: str = "D",  # Changed from "1d" to "D" for daily data (spot API format)
    days_back: int = 5000  # Increased to fetch more historical data
) -> Dict[str, List[Candlestick]]:
    """
    Collect historical spot market candlestick data for the given symbols.
    
    Args:
        symbols: List of trading pair symbols
        interval: Time interval for candlesticks (1,3,5,15,30,60,120,240,360,720,D,M,W)
        days_back: Number of days of historical data to fetch (default: 5000)
    
    Returns:
        Dictionary mapping symbols to lists of Candlestick objects
    """
    persistence = SpotDataPersistence()
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
    
    logger.info(f"Fetching {days_back} days of spot market data from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    logger.info(f"Using interval: {interval}")
    
    all_data = {}
    for symbol in symbols:
        logger.info(f"Fetching spot data for {symbol}...")
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
                    f"Fetched {len(candles)} candles for {symbol} "
                    f"(from {earliest.date()} to {latest.date()})"
                )
            else:
                logger.info(f"Fetched {len(candles)} candles for {symbol}")
                
        except Exception as e:
            logger.error(f"Error fetching spot data for {symbol}: {e}")
            continue
    
    return all_data

if __name__ == "__main__":
    # List of symbols to fetch data for
    symbols = ["BTCUSDT"]  # Add more symbols as needed
    
    # Collect historical data
    data = collect_spot_historical_data(symbols)
    
    # Print summary
    for symbol, candles in data.items():
        if candles:
            earliest = datetime.fromtimestamp(candles[0].open_time / 1000)
            latest = datetime.fromtimestamp(candles[-1].open_time / 1000)
            logger.info(
                f"{symbol}: {len(candles)} candles from {earliest.date()} to {latest.date()}"
            ) 