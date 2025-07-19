#!/usr/bin/env python
import os
import sys
import logging
import argparse
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent.parent))

from rl.data.fetch_etf_data import fetch_multiple_etfs, fetch_historical_etf_data
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.ingest_etf_csv_to_raw import get_all_instruments_from_selection_table, get_etf_symbols_to_ingest, get_conn
from rl.data.generate_etf_features import generate_features

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"etf_ingestion_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("etf_ingestion")

def create_etf_raw_table_if_not_exists(conn):
    """Ensure the ETF raw data table exists."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS etf_raw (
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        instrument TEXT NOT NULL,
        granularity TEXT NOT NULL,
        open DOUBLE PRECISION,
        high DOUBLE PRECISION,
        low DOUBLE PRECISION,
        close DOUBLE PRECISION,
        volume DOUBLE PRECISION,
        PRIMARY KEY (timestamp, instrument, granularity)
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_table_sql)
    conn.commit()
    logger.info("Ensured table etf_raw exists.")

def create_etf_features_table_if_not_exists(conn, table_name="etf_features"):
    """Ensure the ETF features table exists."""
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        instrument TEXT NOT NULL,
        granularity TEXT NOT NULL,
        features JSONB,
        PRIMARY KEY (timestamp, instrument, granularity)
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_table_sql)
    conn.commit()
    logger.info(f"Ensured table {table_name} exists.")

def ingest_etf_data_from_yfinance(symbols, period="max", interval="1d"):
    """
    Fetch ETF data from yfinance and ingest it into the etf_raw table.
    
    Args:
        symbols: List of ETF symbols to fetch
        period: Time period to fetch (e.g., "1y", "2y", "5y", "10y", "max")
        interval: Data interval (e.g., "1d" for daily)
        
    Returns:
        Number of records ingested
    """
    logger.info(f"Fetching data for {len(symbols)} ETF symbols from yfinance")
    
    # Fetch data for all symbols
    etf_data = fetch_multiple_etfs(symbols, period, interval)
    
    # Connect to database
    conn = get_conn()
    try:
        # Ensure table exists
        create_etf_raw_table_if_not_exists(conn)
        
        # Keep track of records inserted
        total_records = 0
        
        # Insert data for each ETF
        for symbol, df in etf_data.items():
            logger.info(f"Processing data for {symbol}: {len(df)} rows")
            
            # Standardize column names
            if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
                # Try to map from capitalized column names
                column_map = {}
                for expected, possible in [
                    ('open', ['Open', 'OPEN']), 
                    ('high', ['High', 'HIGH']), 
                    ('low', ['Low', 'LOW']), 
                    ('close', ['Close', 'CLOSE']), 
                    ('volume', ['Volume', 'VOLUME'])
                ]:
                    for p in possible:
                        if p in df.columns:
                            column_map[p] = expected
                df = df.rename(columns=column_map)
            
            # Prepare data for insert
            records = []
            for idx, row in df.iterrows():
                # Convert index to timestamp if needed
                timestamp = pd.Timestamp(idx) if not isinstance(idx, pd.Timestamp) else idx
                
                records.append({
                    "timestamp": timestamp,
                    "instrument": symbol,
                    "granularity": interval,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)), 
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0))
                })
            
            # Insert into database
            insert_sql = """
            INSERT INTO etf_raw (timestamp, instrument, granularity, open, high, low, close, volume)
            VALUES (%(timestamp)s, %(instrument)s, %(granularity)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
            ON CONFLICT (timestamp, instrument, granularity) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
            """
            
            # Insert in batches
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                with conn.cursor() as cur:
                    for record in batch:
                        cur.execute(insert_sql, record)
                conn.commit()
                logger.info(f"Inserted batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size} for {symbol}")
            
            total_records += len(records)
            logger.info(f"Inserted {len(records)} records for {symbol}")
        
        logger.info(f"Total records inserted: {total_records}")
        return total_records
        
    except Exception as e:
        logger.error(f"Error ingesting ETF data: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def generate_and_store_etf_features(symbols, granularity="D", features_table="etf_features"):
    """
    Generate features for ETF data and store in the features table.
    
    Args:
        symbols: List of ETF symbols to process
        granularity: Data granularity
        features_table: Name of the table to store features
        
    Returns:
        Number of records with features generated
    """
    logger.info(f"Generating features for {len(symbols)} ETF symbols")
    
    # Connect to database
    conn = get_conn()
    try:
        # Ensure features table exists
        create_etf_features_table_if_not_exists(conn, features_table)
        
        # Track records processed
        total_records = 0
        success_count = 0
        error_count = 0
        
        # Process each ETF
        for symbol in symbols:
            try:
                # Fetch raw data
                logger.info(f"Fetching raw data for {symbol}")
                df_raw = fetch_raw_etf_data(symbol, granularity)
                
                if df_raw is None or df_raw.empty:
                    logger.warning(f"No raw data available for {symbol}. Skipping feature generation.")
                    error_count += 1
                    continue
                
                try:
                    # Generate features
                    logger.info(f"Generating features for {symbol}")
                    df_features = generate_features(df_raw)
                    
                    if df_features is None or df_features.empty:
                        logger.warning(f"No features generated for {symbol}. Skipping database insert.")
                        error_count += 1
                        continue
                except Exception as feature_error:
                    logger.error(f"Error generating features for {symbol}: {str(feature_error)}")
                    error_count += 1
                    continue
                
                # Prepare data for insert
                inserted = 0
                
                # Insert each row
                with conn.cursor() as cur:
                    for timestamp, row in df_features.iterrows():
                        # Convert features to JSON
                        features_json = {}
                        for col in df_features.columns:
                            # Handle NaN and inf values before JSON conversion
                            value = row[col]
                            if pd.isna(value) or np.isnan(value) if isinstance(value, float) else False:
                                features_json[col] = None
                            elif np.isinf(value) if isinstance(value, float) else False:
                                features_json[col] = None
                            else:
                                features_json[col] = float(value)
                        
                        # Insert the record
                        insert_sql = f"""
                        INSERT INTO {features_table} (timestamp, instrument, granularity, features)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (timestamp, instrument, granularity) 
                        DO UPDATE SET features = EXCLUDED.features
                        """
                        
                        cur.execute(insert_sql, (
                            timestamp,
                            symbol,
                            granularity,
                            json.dumps(features_json)
                        ))
                        
                        inserted += 1
                
                # Commit after each ETF
                conn.commit()
                
                logger.info(f"Inserted {inserted} feature records for {symbol}")
                total_records += inserted
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                # Continue with next ETF
                conn.rollback()
                error_count += 1
        
        logger.info(f"Feature generation complete: {success_count} ETFs processed successfully, {error_count} errors")
        return total_records
        
    except Exception as e:
        logger.error(f"Error in feature generation: {str(e)}")
        return 0
    finally:
        conn.close()

def main():
    """Main function to run the ETF data ingestion pipeline."""
    parser = argparse.ArgumentParser(description='Ingest ETF data from yfinance and generate features')
    parser.add_argument('--symbols', type=str, nargs='+', help='ETF symbols to process (optional)')
    parser.add_argument('--period', type=str, default="max", help='Time period to fetch (e.g., "1y", "5y", "max")')
    parser.add_argument('--generate-features', action='store_true', help='Generate features after data ingestion')
    parser.add_argument('--features-only', action='store_true', help='Skip data ingestion and only generate features')
    
    args = parser.parse_args()
    
    # Get ETF symbols
    etf_symbols = args.symbols
    if not etf_symbols:
        # Auto-detect ETF symbols from DB
        try:
            all_instruments = get_all_instruments_from_selection_table()
            etf_symbols = get_etf_symbols_to_ingest()
            if not etf_symbols:
                # Fallback to some common ETFs
                etf_symbols = ["SPY", "QQQ", "IWM", "GLD", "SLV", "VXX", "EEM", "XLF", "XLE"]
        except Exception as e:
            logger.error(f"Error auto-detecting ETF symbols: {str(e)}")
            # Fallback to some common ETFs
            etf_symbols = ["SPY", "QQQ", "IWM", "GLD", "SLV", "VXX", "EEM", "XLF", "XLE"]
    
    logger.info(f"Processing ETF symbols: {etf_symbols}")
    
    if not args.features_only:
        # Ingest raw data
        logger.info("Starting ETF data ingestion from yfinance")
        try:
            record_count = ingest_etf_data_from_yfinance(etf_symbols, args.period, "1d")
            logger.info(f"Successfully ingested {record_count} ETF data records")
        except Exception as e:
            logger.error(f"Failed to ingest ETF data: {str(e)}")
            if not args.generate_features:
                return
    
    if args.generate_features or args.features_only:
        # Generate features
        logger.info("Starting ETF feature generation")
        try:
            feature_count = generate_and_store_etf_features(etf_symbols, "D")
            logger.info(f"Successfully generated {feature_count} ETF feature records")
        except Exception as e:
            logger.error(f"Failed to generate ETF features: {str(e)}")
    
    logger.info("ETF data processing complete")

if __name__ == "__main__":
    main() 