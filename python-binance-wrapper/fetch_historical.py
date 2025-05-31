"""
Script to fetch historical daily candlestick data from Binance.US.
"""
import os
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
from typing import List, Dict, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceHistoricalData:
    """Handles fetching and storing historical data from Binance.US."""
    
    BASE_URL = "https://api.binance.us"
    
    def __init__(self, data_dir: str = "data/binance"):
        """
        Initialize the historical data fetcher.
        
        Args:
            data_dir: Directory to store historical data
        """
        self.data_dir = data_dir
        self.session = requests.Session()
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_data_path(self, symbol: str) -> str:
        """Get the path for a symbol's data file."""
        return os.path.join(self.data_dir, f"{symbol.lower()}_daily.csv")
    
    def _load_existing_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load existing data for a symbol if it exists."""
        data_path = self._get_data_path(symbol)
        if os.path.exists(data_path):
            try:
                df = pd.read_csv(data_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            except Exception as e:
                logger.error(f"Error loading existing data for {symbol}: {e}")
        return None
    
    def _save_data(self, symbol: str, df: pd.DataFrame):
        """Save data to CSV file."""
        data_path = self._get_data_path(symbol)
        df.to_csv(data_path, index=False)
        logger.info(f"Saved {len(df)} records for {symbol} to {data_path}")
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Fetch klines (candlestick data) from Binance.US.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Time interval (e.g., '1d' for daily)
            start_time: Start time in milliseconds (optional)
            end_time: End time in milliseconds (optional)
            limit: Number of klines to fetch (max 1000)
            
        Returns:
            List of kline data dictionaries
        """
        endpoint = f"{self.BASE_URL}/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000)  # Binance.US max limit is 1000
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
    
    def fetch_historical_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> bool:
        """
        Fetch historical daily data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Set default dates if not provided
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=5000)  # Default to 5000 days
            
            # Normalize dates to start of day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            logger.info(f"Fetching historical data for {symbol} from {start_date} to {end_date}")
            
            # Load existing data
            existing_df = self._load_existing_data(symbol)
            if existing_df is not None:
                # Get the latest timestamp from existing data
                latest_time = existing_df['timestamp'].max()
                if latest_time >= end_date:
                    logger.info(f"Data for {symbol} is already up to date")
                    return True
                start_date = latest_time + timedelta(days=1)
                logger.info(f"Resuming from {start_date}")
            
            # Initialize empty list for all klines
            all_klines = []
            current_end = end_date
            
            # Fetch data in chunks until we reach the start date
            while current_end > start_date:
                # Convert datetime to timestamp in milliseconds
                end_timestamp = int(current_end.timestamp() * 1000)
                
                # Fetch a chunk of klines
                klines = self.fetch_klines(
                    symbol=symbol,
                    interval="1d",
                    end_time=end_timestamp,
                    limit=1000
                )
                
                if not klines:
                    break
                
                # Convert klines to DataFrame
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Filter out any data before our start date
                df = df[df['timestamp'] >= start_date]
                
                if len(df) == 0:
                    break
                
                all_klines.append(df)
                
                # Update end time for next chunk
                current_end = df['timestamp'].min() - timedelta(days=1)
                
                # Add a small delay to avoid rate limits
                time.sleep(0.1)
            
            if not all_klines:
                logger.warning(f"No new data collected for {symbol}")
                return False
            
            # Combine all chunks
            new_df = pd.concat(all_klines)
            
            # Combine with existing data if any
            if existing_df is not None:
                combined_df = pd.concat([existing_df, new_df])
                combined_df = combined_df.drop_duplicates(subset=['timestamp'])
                combined_df = combined_df.sort_values('timestamp')
            else:
                combined_df = new_df
            
            # Save combined data
            self._save_data(symbol, combined_df)
            
            logger.info(f"Successfully collected {len(new_df)} new daily candles for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return False

def main():
    """Main function to fetch historical data for multiple symbols."""
    # List of symbols to fetch data for (top 20 non-stablecoin instruments from CoinMarketCap)
    symbols = [
        "BTCUSDT",   # Bitcoin
        "ETHUSDT",   # Ethereum
        "XRPUSDT",   # XRP
        "BNBUSDT",   # BNB
        "SOLUSDT",   # Solana
        "DOGEUSDT",  # Dogecoin
        "ADAUSDT",   # Cardano
        "TRXUSDT",   # TRON
        "AVAXUSDT",  # Avalanche
        "DOTUSDT",   # Polkadot
        "LINKUSDT",  # Chainlink
        "MATICUSDT", # Polygon
        "SHIBUSDT",  # Shiba Inu
        "UNIUSDT",   # Uniswap
        "LTCUSDT",   # Litecoin
        "ATOMUSDT",  # Cosmos
        "XLMUSDT",   # Stellar
        "ALGOUSDT",  # Algorand
        "FILUSDT",   # Filecoin
        "ICPUSDT"    # Internet Computer
    ]
    
    # Initialize data fetcher
    fetcher = BinanceHistoricalData()
    
    # Fetch data for each symbol
    for symbol in symbols:
        logger.info(f"Processing {symbol}...")
        success = fetcher.fetch_historical_data(symbol)
        if success:
            # Load and display data summary
            df = fetcher._load_existing_data(symbol)
            if df is not None:
                earliest = df['timestamp'].min()
                latest = df['timestamp'].max()
                logger.info(f"{symbol}: {len(df)} candles from {earliest.date()} to {latest.date()}")
        else:
            logger.error(f"Failed to fetch data for {symbol}")

if __name__ == "__main__":
    main() 