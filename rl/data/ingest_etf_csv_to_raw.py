#!/usr/bin/env python
import os
import psycopg2
import pandas as pd
from typing import List, Dict
import re

# Assuming rl.constants and db connection are accessible
try:
    from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
except ImportError:
    # Adjust sys.path if running this script directly from rl/data/
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    from constants import PAIRS_BY_LIQUIDITY_OANDA

DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# The directory where the CSV files are located, relative to workspace root
CSV_DIR = "etf_data"

def get_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def get_all_instruments_from_selection_table() -> Dict[str, List[str]]:
    """Fetches all instruments and their currently selected features."""
    query = "SELECT instrument, feature_name FROM selected_features_per_instrument ORDER BY instrument, rank;"
    instrument_features = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            for row in cur:
                instrument, feature_name = row
                if instrument not in instrument_features:
                    instrument_features[instrument] = []
                instrument_features[instrument].append(feature_name)
    return instrument_features

def get_etf_symbols_to_ingest() -> List[str]:
    """Derives ETF symbols from the full list of instruments in selected_features_per_instrument."""
    all_selected_instruments = get_all_instruments_from_selection_table()
    etf_symbols = []
    sorted_instruments = sorted(list(all_selected_instruments.keys()))
    for inst in sorted_instruments:
        if inst not in PAIRS_BY_LIQUIDITY_OANDA:
            etf_symbols.append(inst)
    print(f"Derived {len(etf_symbols)} potential ETF symbols. Capping at 34 if more.")
    # Ensure we only take the number of ETFs we expect (e.g., 34)
    # This assumes the list from selected_features_per_instrument is the definitive source for ETF names
    return etf_symbols[:34] 

def create_etf_raw_table_if_not_exists(conn):
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
    print(f"Ensured table etf_raw exists.")

def ingest_etf_csv(conn, symbol: str):
    csv_filename = f"{symbol}_daily_yf.csv"
    csv_path = os.path.join(CSV_DIR, csv_filename)

    if not os.path.exists(csv_path):
        print(f"CSV file not found for {symbol}: {csv_path}. Skipping.")
        return 0

    try:
        df = pd.read_csv(csv_path)
        print(f"Read {len(df)} rows from {csv_path} for {symbol}")
    except Exception as e:
        print(f"Error reading CSV {csv_path}: {e}. Skipping {symbol}.")
        return 0

    # Standardize column names (Yahoo Finance CSVs can vary slightly)
    # Expected columns in etf_raw: timestamp, open, high, low, close, volume
    # CSV columns typically: Date, Open, High, Low, Close, Adj Close, Volume
    column_map = {
        'Date': 'timestamp',
        'timestamp': 'timestamp', # If already named timestamp
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'raw_close', # Read 'Close' into a temp column
        'Adj Close': 'close', # Use 'Adj Close' as the final 'close' price
        'Volume': 'volume'
    }
    df.rename(columns=column_map, inplace=True)

    # Select and ensure required columns exist
    required_cols_for_db = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    cols_to_insert = []
    for col in required_cols_for_db:
        if col in df.columns:
            cols_to_insert.append(col)
        elif col == 'close' and 'raw_close' in df.columns: # Fallback if 'Adj Close' was missing but 'Close' exists
            print(f"Warning: 'Adj Close' not found for {symbol}, using 'Close' as 'close'.")
            df.rename(columns={'raw_close': 'close'}, inplace=True)
            cols_to_insert.append('close')
        else:
            print(f"Error: Required column '{col}' not found in CSV for {symbol} after mapping. Skipping {symbol}.")
            return 0
    
    df = df[cols_to_insert].copy() # Keep only the columns we need

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True) # Drop rows where timestamp couldn't be parsed
    
    # Ensure numeric types and handle NaNs for OHLCV
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.fillna(0, inplace=True) # Replace NaNs in numeric columns with 0, or use more robust imputation

    df['instrument'] = symbol
    df['granularity'] = 'D'

    # Reorder columns to match etf_raw table structure for insert if needed, though psycopg2 can handle dicts
    df = df[['timestamp', 'instrument', 'granularity', 'open', 'high', 'low', 'close', 'volume']]

    # Ingest into database
    insert_sql = """
    INSERT INTO etf_raw (timestamp, instrument, granularity, open, high, low, close, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (timestamp, instrument, granularity) DO NOTHING;
    """
    
    inserted_count = 0
    with conn.cursor() as cur:
        for record_tuple in df.itertuples(index=False, name=None):
            try:
                cur.execute(insert_sql, record_tuple)
                inserted_count += 1
            except Exception as e_ins:
                print(f"Error inserting row for {symbol}: {record_tuple} - {e_ins}")
                # Optionally, decide if to break or continue
    conn.commit()
    print(f"Inserted/updated {inserted_count} rows for {symbol} into etf_raw.")
    return inserted_count

def main():
    etf_symbols = get_etf_symbols_to_ingest()
    if not etf_symbols:
        print("No ETF symbols to ingest. Exiting.")
        return

    print(f"Target ETF symbols for ingestion ({len(etf_symbols)}): {etf_symbols}")

    conn = get_conn()
    try:
        create_etf_raw_table_if_not_exists(conn)
        total_rows_ingested = 0
        for symbol in etf_symbols:
            print(f"--- Processing {symbol} ---")
            rows = ingest_etf_csv(conn, symbol)
            total_rows_ingested += rows
        print(f"\n--- Ingestion Complete ---")
        print(f"Total rows ingested across all ETFs: {total_rows_ingested}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 