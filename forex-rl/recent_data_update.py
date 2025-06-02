#!/usr/bin/env python3
"""
Update recent forex data and store in aligned_candles table
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_recent_data(days=10):
    """Update recent candles for all forex pairs"""
    logger.info(f"Updating recent {days} days of data")
    
    # Initialize OANDA client
    client = OandaDataClient()
    
    # Connect to SQLite database
    conn = sqlite3.connect(config.data_dir + '/forex_candles.sqlite3')
    cursor = conn.cursor()
    
    # Create aligned_candles table if it doesn't exist
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
        logger.info(f"Updating {instrument}")
        
        # Fetch recent data from OANDA (with timezone UTC)
        df = client.fetch_recent_data(instrument, days=days)
        
        if df.empty:
            logger.warning(f"No data returned for {instrument}")
            continue
            
        logger.info(f"Retrieved {len(df)} records for {instrument}")
        
        # Convert datetime index to string
        data_to_upsert = []
        for time, row in df.iterrows():
            # Convert time to string with UTC timezone
            time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            data_to_upsert.append((
                instrument,
                time_str,
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
            
        # Upsert into database
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
            logger.info(f"Upserted {len(data_to_upsert)} records for {instrument}")
        except Exception as e:
            logger.error(f"Database error for {instrument}: {e}")
            conn.rollback()
            
    conn.close()
    logger.info("Recent data update complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update recent forex data')
    parser.add_argument('--days', type=int, default=10, help='Number of days to fetch')
    args = parser.parse_args()
    
    update_recent_data(days=args.days)
