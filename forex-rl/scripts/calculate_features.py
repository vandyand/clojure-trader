#!/usr/bin/env python3
"""
Calculate Fibonacci-based features for forex instruments
Features: feat_i = (close_t / close_{t-i}) - 1
Where i is from the first 15 Fibonacci numbers
"""

import sqlite3
import pandas as pd
import numpy as np
import argparse
import logging
import os
from datetime import datetime

# Define Fibonacci periods directly
FIBONACCI_PERIODS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def calculate_features(db_path: str, instrument: str):
    """
    Calculate Fibonacci features for a single instrument
    
    Args:
        db_path: Path to SQLite database
        instrument: Forex pair (e.g., "EUR_USD")
    """
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        
        # Query candles for this instrument
        query = f"""
        SELECT time, close 
        FROM candles 
        WHERE instrument = '{instrument}'
        ORDER BY time ASC
        """
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            logger.warning(f"No data found for {instrument}")
            return False
        
        # Convert time to datetime and set as index
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        # Create a new DataFrame to store features
        features_df = pd.DataFrame(index=df.index)
        
        # Calculate features for each Fibonacci period
        for period in FIBONACCI_PERIODS:
            col_name = f'feat_{period}'
            
            # Shift the close prices by the Fibonacci period
            shifted_close = df['close'].shift(period)
            
            # For early periods with no data, use the first available close
            first_valid_close = df['close'].iloc[0]
            shifted_close.fillna(first_valid_close, inplace=True)
            
            # Calculate feature: (current close / close_{t-period}) - 1
            features_df[col_name] = (df['close'] / shifted_close) - 1
        
        # Add instrument column
        features_df['instrument'] = instrument
        
        # Save features to database
        features_df.reset_index(inplace=True)
        features_df['time'] = features_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create features table if not exists
        columns = ', '.join([f'feat_{p} REAL' for p in FIBONACCI_PERIODS])
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS features (
            instrument TEXT,
            time TEXT,
            {columns},
            PRIMARY KEY (instrument, time)
        );
        """
        
        conn.execute(create_table_query)
        conn.commit()
        
        # Insert features into database
        features_df.to_sql('features', conn, if_exists='append', index=False)
        
        logger.info(f"Calculated features for {instrument} with {len(features_df)} rows")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {instrument}: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def calculate_all_features(db_path: str, instruments: list = None):
    """
    Calculate features for all instruments
    
    Args:
        db_path: Path to SQLite database
        instruments: List of instruments to process (default: all in database)
    """
    if instruments is None:
        # Get all distinct instruments from candles table
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT instrument FROM candles")
            instruments = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching instruments: {str(e)}")
            return
        finally:
            if conn:
                conn.close()
    
    logger.info(f"Calculating features for {len(instruments)} instruments")
    
    success_count = 0
    for instrument in instruments:
        if calculate_features(db_path, instrument):
            success_count += 1
    
    logger.info(f"Completed feature calculation: {success_count}/{len(instruments)} instruments processed")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Calculate Fibonacci features for forex instruments')
    parser.add_argument('--db-path', default='data/forex_candles.sqlite3', 
                        help='Path to SQLite database')
    parser.add_argument('--instrument', default='EUR_USD', 
                        help='Specific instrument to process (default: EUR_USD)')
    parser.add_argument('--all', action='store_true', 
                        help='Process all instruments')
    parser.add_argument('--output-dir', default='data', 
                        help='Output directory for database')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    db_path = os.path.join(args.output_dir, 'forex_candles.sqlite3')
    
    if args.all:
        calculate_all_features(db_path)
    else:
        calculate_features(db_path, args.instrument)

if __name__ == '__main__':
    main()
