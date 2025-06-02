#!/usr/bin/env python3
"""
Update recent forex data and store directly into the 'aligned_candles' table.

Note: This script directly updates 'aligned_candles'. If 'aligned_features'
needs to be updated based on these new candles, 'align_data.py' or a similar
feature calculation script should be run afterwards.
"""

import sqlite3
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from data.oanda_client import OandaDataClient
from config.settings import config
from config.forex_pairs import FOREX_PAIRS
import argparse
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_recent_data(days=10):
    """Update recent candles for all forex pairs directly in the 'aligned_candles' table."""
    logger.info(f"Updating recent {days} days of data directly in the 'aligned_candles' table.")
    
    # Initialize OANDA client
    client = OandaDataClient()
    
    # Connect to SQLite database
    db_path = os.path.join(config.data_dir, 'forex_candles.sqlite3')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure the 'aligned_candles' table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aligned_candles (
        instrument TEXT NOT NULL,
        time TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume INTEGER NOT NULL,
        PRIMARY KEY (instrument, time)
    );
    """)
    conn.commit()
    
    # Fetch and update data for each instrument
    for instrument in FOREX_PAIRS:
        logger.info(f"Fetching recent data for {instrument} from OANDA...")
        
        # Fetch recent data from OANDA.
        # Fetching 'days + 1' to ensure we get enough data to cover the requested period
        # and potentially align with previous day's data if needed for continuity.
        df = client.fetch_historical_data(instrument, granularity="D", count=days + 1)
        
        if df.empty:
            logger.warning(f"No data returned for {instrument}. Skipping.")
            continue
            
        logger.info(f"Retrieved {len(df)} records for {instrument}.")
        
        # Convert datetime index to string and normalize to date only (midnight UTC)
        # This is crucial for consistency with how 'align_data.py' handles time.
        data_to_upsert = []
        for time_idx, row in df.iterrows():
            # Normalize time to YYYY-MM-DD format for daily data
            time_str = time_idx.strftime('%Y-%m-%d') 
            data_to_upsert.append((
                instrument,
                time_str,
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
            
        # Upsert into 'aligned_candles' table
        query = """
        INSERT INTO aligned_candles (instrument, time, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument, time) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume
        """
        try:
            cursor.executemany(query, data_to_upsert)
            conn.commit()
            logger.info(f"Upserted {len(data_to_upsert)} records for {instrument} into 'aligned_candles' table.")
        except Exception as e:
            logger.error(f"Database error for {instrument}: {e}. Rolling back changes for this instrument.")
            conn.rollback()
            
    conn.close()
    logger.info("Recent data update to 'aligned_candles' table complete.")
    logger.info("Consider running 'python align_data.py <db_path>' if you need to ensure full time-series alignment (e.g., forward-filling missing dates) or to update 'aligned_features'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update recent forex data directly in the aligned_candles table.')
    parser.add_argument('--days', type=int, default=10, help='Number of recent days to fetch and update.')
    args = parser.parse_args()
    
    update_recent_data(days=args.days)
