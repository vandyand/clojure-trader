"""
Persistence layer for storing and retrieving historical spot market candlestick data using SQLite.
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from bitunix.client import BitUnixClient
from bitunix.models import Candlestick

logger = logging.getLogger(__name__)

class SpotDataPersistence:
    """Handles persistence of historical spot market candlestick data using SQLite."""
    
    def __init__(self, db_path: str = "data/spot_historical_data.db", data_dir: str = "data/spot"):
        """
        Initialize the persistence layer.
        
        Args:
            db_path: Path to the SQLite database file
            data_dir: Directory to store spot market data
        """
        self.db_path = db_path
        self.data_dir = data_dir
        self.client = BitUnixClient()
        self._init_db()
        os.makedirs(data_dir, exist_ok=True)
    
    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        # Create data directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create candlesticks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spot_candlesticks (
                    symbol TEXT,
                    open_time INTEGER,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    quote_volume REAL,
                    kline_type TEXT,
                    PRIMARY KEY (symbol, open_time)
                )
            """)
            
            # Create metadata table to track last update times
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spot_metadata (
                    symbol TEXT PRIMARY KEY,
                    last_update_time INTEGER,
                    earliest_candle_time INTEGER,
                    latest_candle_time INTEGER
                )
            """)
            
            conn.commit()
    
    def get_historical_data(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Candlestick]:
        """
        Get historical spot market data for a symbol, fetching from API only if necessary.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (e.g., '1d')
            start_time: Start time in milliseconds (optional)
            end_time: End time in milliseconds (optional)
            
        Returns:
            List of Candlestick objects
        """
        # Set default times if not provided
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
        if start_time is None:
            start_time = int((datetime.now() - timedelta(days=5000)).timestamp() * 1000)
        
        # Get data from database
        db_data = self._get_from_db(symbol, start_time, end_time)
        
        # Check if we need to fetch more data
        missing_ranges = self._find_missing_ranges(db_data, start_time, end_time)
        
        if missing_ranges:
            # Fetch missing data from API
            for range_start, range_end in missing_ranges:
                new_data = self._fetch_from_api(symbol, interval, range_end)
                if new_data:
                    # Save new data to database
                    self._save_to_db(symbol, new_data)
                    # Add to our results
                    db_data.extend(new_data)
        
        # Sort by open_time and filter by time range
        db_data.sort(key=lambda x: x.open_time)
        return [c for c in db_data if start_time <= c.open_time <= end_time]
    
    def _get_from_db(
        self,
        symbol: str,
        start_time: int,
        end_time: int
    ) -> List[Candlestick]:
        """Retrieve data from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT open_time, open_price, high_price, low_price, close_price,
                       volume, quote_volume, kline_type
                FROM spot_candlesticks
                WHERE symbol = ? AND open_time BETWEEN ? AND ?
                ORDER BY open_time
            """, (symbol, start_time, end_time))
            
            return [
                Candlestick(
                    open_time=row[0],
                    open_price=row[1],
                    high_price=row[2],
                    low_price=row[3],
                    close_price=row[4],
                    volume=row[5],
                    quote_volume=row[6],
                    kline_type=row[7]
                )
                for row in cursor.fetchall()
            ]
    
    def _save_to_db(self, symbol: str, candles: List[Candlestick]):
        """Save candlestick data to SQLite database."""
        if not candles:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Prepare data for insertion
            data = [
                (
                    symbol,
                    c.open_time,
                    c.open_price,
                    c.high_price,
                    c.low_price,
                    c.close_price,
                    c.volume,
                    c.quote_volume,
                    c.kline_type
                )
                for c in candles
            ]
            
            # Insert or replace data
            cursor.executemany("""
                INSERT OR REPLACE INTO spot_candlesticks
                (symbol, open_time, open_price, high_price, low_price, close_price,
                 volume, quote_volume, kline_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            # Update metadata
            earliest_time = min(c.open_time for c in candles)
            latest_time = max(c.open_time for c in candles)
            cursor.execute("""
                INSERT OR REPLACE INTO spot_metadata
                (symbol, last_update_time, earliest_candle_time, latest_candle_time)
                VALUES (?, ?, ?, ?)
            """, (symbol, int(datetime.now().timestamp() * 1000), earliest_time, latest_time))
            
            conn.commit()
    
    def _fetch_from_api(
        self,
        symbol: str,
        interval: str,
        end_time: int
    ) -> List[Candlestick]:
        """
        Fetch data from Bitunix spot market API in chunks of 500 candles.
        Makes sequential requests going back in time until we reach the start_time.
        """
        all_candles = []
        current_end = end_time // 1000  # Convert to seconds for spot API
        chunk_count = 0
        
        logger.info(f"Starting spot API fetch for {symbol} (end_time: {datetime.fromtimestamp(current_end)})")
        
        while True:
            try:
                chunk_count += 1
                logger.info(f"Fetching chunk {chunk_count} for {symbol} (end_time: {datetime.fromtimestamp(current_end)})")
                
                # Fetch a chunk of candles
                chunk = self.client.get_spot_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    end_time=current_end,
                    limit=500  # Maximum allowed by spot API
                )
                
                if not chunk:
                    logger.info(f"No more data available for {symbol}")
                    break
                    
                all_candles.extend(chunk)
                logger.info(f"Fetched {len(chunk)} candles in chunk {chunk_count}")
                
                # Update end time for next chunk (go back in time)
                # Use the earliest candle's open_time as the new end time
                earliest_time = min(c.open_time for c in chunk) // 1000  # Convert to seconds
                if earliest_time >= current_end:  # No more data available
                    logger.info(f"Reached earliest available data for {symbol}")
                    break
                    
                current_end = earliest_time - 1  # Subtract 1 second to avoid overlap
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching data chunk for {symbol}: {e}")
                break
        
        logger.info(f"Completed spot API fetch for {symbol}: {len(all_candles)} total candles in {chunk_count} chunks")
        return all_candles
    
    def _find_missing_ranges(
        self,
        existing_data: List[Candlestick],
        start_time: int,
        end_time: int
    ) -> List[Tuple[int, int]]:
        """
        Find time ranges where data is missing.
        
        Args:
            existing_data: List of existing Candlestick objects
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of (start_time, end_time) tuples for missing ranges
        """
        if not existing_data:
            return [(start_time, end_time)]
        
        # Sort existing data by time
        existing_data.sort(key=lambda x: x.open_time)
        
        # Find gaps in the data
        missing_ranges = []
        current_time = start_time
        
        for candle in existing_data:
            if candle.open_time > current_time:
                missing_ranges.append((current_time, candle.open_time - 86400000))  # -1 day in ms
            current_time = candle.open_time + 86400000  # +1 day in ms
        
        # Check if we need data after the last candle
        if current_time < end_time:
            missing_ranges.append((current_time, end_time))
        
        return missing_ranges
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM spot_candlesticks")
            return [row[0] for row in cursor.fetchall()]
    
    def get_symbol_metadata(self, symbol: str) -> Optional[Dict]:
        """Get metadata for a symbol."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_update_time, earliest_candle_time, latest_candle_time
                FROM spot_metadata
                WHERE symbol = ?
            """, (symbol,))
            row = cursor.fetchone()
            if row:
                return {
                    'last_update_time': row[0],
                    'earliest_candle_time': row[1],
                    'latest_candle_time': row[2]
                }
            return None
    
    def _get_data_path(self, symbol: str) -> str:
        """Get the path for a symbol's data file."""
        return os.path.join(self.data_dir, f"{symbol.lower()}_spot.csv")
    
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
    
    def _fetch_chunk(
        self,
        symbol: str,
        end_time: int,
        interval: str = "D",  # Changed from "1d" to "D" for daily data (spot API format)
        limit: int = 500  # Maximum allowed by API
    ) -> List[Candlestick]:
        """
        Fetch a chunk of historical data.
        
        Args:
            symbol: Trading pair symbol
            end_time: End timestamp in seconds
            interval: Time interval (default: D for daily data)
            limit: Number of candles to fetch (default: 500, maximum allowed)
            
        Returns:
            List of Candlestick objects
        """
        try:
            # For daily data, we want to ensure we're not getting duplicate days
            # Convert end_time to start of day
            end_date = datetime.fromtimestamp(end_time)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_timestamp = int(end_date.timestamp())
            
            logger.info(f"Fetching {interval} data for {symbol} with end_time: {end_date}")
            
            candles = self.client.get_spot_historical_klines(
                symbol=symbol,
                interval=interval,
                end_time=end_timestamp,
                limit=limit
            )
            
            if candles:
                # Debug log the first and last candle times
                first_candle = candles[0]
                last_candle = candles[-1]
                logger.info(f"First candle: {datetime.fromtimestamp(first_candle.open_time/1000)}")
                logger.info(f"Last candle: {datetime.fromtimestamp(last_candle.open_time/1000)}")
                logger.info(f"Total candles in chunk: {len(candles)}")
                
                # Check for duplicate timestamps
                timestamps = [c.open_time for c in candles]
                if len(timestamps) != len(set(timestamps)):
                    logger.warning(f"Found duplicate timestamps in chunk for {symbol}")
                    # Log the duplicates
                    seen = set()
                    duplicates = [x for x in timestamps if x in seen or seen.add(x)]
                    logger.warning(f"Duplicate timestamps: {[datetime.fromtimestamp(ts/1000) for ts in duplicates]}")
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} at {end_time}: {e}")
            return []
    
    def _process_symbol(self, symbol: str, start_date: datetime, end_date: datetime) -> bool:
        """
        Process a single symbol's data collection.
        
        Args:
            symbol: Trading pair symbol
            start_date: Start date for data collection
            end_date: End date for data collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Normalize dates to start of day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            logger.info(f"Processing {symbol} from {start_date} to {end_date}")
            
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
            
            # Initialize empty list for all candles
            all_candles = []
            current_end = end_date
            
            # Fetch data in chunks until we reach the start date
            chunk_count = 0
            while current_end > start_date:
                chunk_count += 1
                logger.info(f"Fetching chunk {chunk_count} for {symbol} (end_time: {current_end})")
                
                # Convert datetime to timestamp in seconds
                end_timestamp = int(current_end.timestamp())
                
                # Fetch chunk of data
                candles = self._fetch_chunk(symbol, end_timestamp)
                if not candles:
                    break
                
                # Filter out any candles that are before our start date
                valid_candles = [c for c in candles if datetime.fromtimestamp(c.open_time / 1000) >= start_date]
                logger.info(f"Chunk {chunk_count}: {len(valid_candles)} valid candles out of {len(candles)} total")
                
                all_candles.extend(valid_candles)
                
                # Update end time for next chunk
                if candles:
                    # Get the earliest candle's date and go back one day
                    earliest_candle = min(candles, key=lambda x: x.open_time)
                    current_end = datetime.fromtimestamp(earliest_candle.open_time / 1000) - timedelta(days=1)
                    logger.info(f"Next chunk will start from: {current_end}")
                else:
                    break
                
                # Add a small delay to avoid rate limits
                time.sleep(0.5)
            
            if not all_candles:
                logger.warning(f"No new data collected for {symbol}")
                return False
            
            # Convert candles to DataFrame
            new_data = []
            for candle in all_candles:
                new_data.append({
                    'timestamp': datetime.fromtimestamp(candle.open_time / 1000),
                    'open': candle.open_price,
                    'high': candle.high_price,
                    'low': candle.low_price,
                    'close': candle.close_price,
                    'volume': candle.volume,
                    'quote_volume': candle.quote_volume
                })
            
            new_df = pd.DataFrame(new_data)
            logger.info(f"Created DataFrame with {len(new_df)} rows")
            
            # Combine with existing data if any
            if existing_df is not None:
                combined_df = pd.concat([existing_df, new_df])
                combined_df = combined_df.drop_duplicates(subset=['timestamp'])
                combined_df = combined_df.sort_values('timestamp')
                logger.info(f"Combined DataFrame has {len(combined_df)} rows after deduplication")
            else:
                combined_df = new_df
            
            # Save combined data
            self._save_data(symbol, combined_df)
            return True
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return False
    
    def collect_historical_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        max_workers: int = 5
    ):
        """
        Collect historical data for multiple symbols in parallel.
        
        Args:
            symbols: List of trading pair symbols
            start_date: Start date for data collection
            end_date: End date for data collection
            max_workers: Maximum number of parallel workers
        """
        logger.info(f"Starting historical data collection for {len(symbols)} symbols")
        logger.info(f"Date range: {start_date} to {end_date}")
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self._process_symbol, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            # Process results as they complete
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    if future.result():
                        successful += 1
                        logger.info(f"Successfully collected data for {symbol}")
                    else:
                        failed += 1
                        logger.error(f"Failed to collect data for {symbol}")
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing {symbol}: {e}")
        
        logger.info(f"Data collection completed. Successful: {successful}, Failed: {failed}") 