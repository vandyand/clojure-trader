"""
Persistence layer for storing and retrieving historical candlestick data using SQLite.
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import time

from bitunix.client import BitUnixClient
from bitunix.models import Candlestick

logger = logging.getLogger(__name__)

class DataPersistence:
    """Handles persistence of historical candlestick data using SQLite."""
    
    def __init__(self, db_path: str = "data/historical_data.db"):
        """
        Initialize the persistence layer.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.client = BitUnixClient()
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        # Create data directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create candlesticks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candlesticks (
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
                CREATE TABLE IF NOT EXISTS metadata (
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
        Get historical data for a symbol, fetching from API only if necessary.
        
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
                new_data = self._fetch_from_api(symbol, interval, range_start, range_end)
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
                FROM candlesticks
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
                INSERT OR REPLACE INTO candlesticks
                (symbol, open_time, open_price, high_price, low_price, close_price,
                 volume, quote_volume, kline_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            # Update metadata
            earliest_time = min(c.open_time for c in candles)
            latest_time = max(c.open_time for c in candles)
            cursor.execute("""
                INSERT OR REPLACE INTO metadata
                (symbol, last_update_time, earliest_candle_time, latest_candle_time)
                VALUES (?, ?, ?, ?)
            """, (symbol, int(datetime.now().timestamp() * 1000), earliest_time, latest_time))
            
            conn.commit()
    
    def _fetch_from_api(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int
    ) -> List[Candlestick]:
        """
        Fetch data from Bitunix API in chunks of 399 candles.
        Makes sequential requests going back in time until we reach the start_time.
        """
        all_candles = []
        current_end = end_time
        chunk_count = 0
        
        logger.info(f"Starting API fetch for {symbol} from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
        
        while current_end > start_time:
            try:
                chunk_count += 1
                logger.info(f"Fetching chunk {chunk_count} for {symbol} (end_time: {datetime.fromtimestamp(current_end/1000)})")
                
                # Calculate a smaller time window (about 400 days)
                window_start = max(start_time, current_end - (400 * 24 * 60 * 60 * 1000))
                
                # Fetch a chunk of candles
                chunk = self.client.market.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=window_start,
                    end_time=current_end,
                    limit=399,  # Maximum allowed by API
                    kline_type="LAST_PRICE"
                )
                
                if not chunk:
                    logger.info(f"No data available for {symbol} in this time window")
                    # Move back by a smaller amount if no data
                    current_end = window_start - 1
                    continue
                    
                all_candles.extend(chunk)
                logger.info(f"Fetched {len(chunk)} candles in chunk {chunk_count}")
                
                # Update end time for next chunk (go back in time)
                # Use the earliest candle's open_time as the new end time
                earliest_time = min(c.open_time for c in chunk)
                if earliest_time >= current_end:  # No more data available
                    logger.info(f"Reached earliest available data for {symbol}")
                    break
                    
                current_end = earliest_time - 1  # Subtract 1ms to avoid overlap
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching data chunk for {symbol}: {e}")
                # Move back by a smaller amount on error
                current_end = window_start - 1
                time.sleep(1)  # Longer delay on error
                continue
        
        logger.info(f"Completed API fetch for {symbol}: {len(all_candles)} total candles in {chunk_count} chunks")
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
            cursor.execute("SELECT DISTINCT symbol FROM candlesticks")
            return [row[0] for row in cursor.fetchall()]
    
    def get_symbol_metadata(self, symbol: str) -> Optional[Dict]:
        """Get metadata for a symbol."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_update_time, earliest_candle_time, latest_candle_time
                FROM metadata
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