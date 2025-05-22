#!/usr/bin/env python3
import sys
import os
# Ensure project root is in sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from rl.data.fetch_oanda import fetch_candles
from rl.data.indicators import add_indicators
import time
from sqlalchemy.dialects.postgresql import JSONB
import numpy as np
import json
from sqlalchemy import Table, MetaData, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
import argparse
import math
import glob
import warnings
from pandas.errors import PerformanceWarning

warnings.filterwarnings("ignore", category=PerformanceWarning, message="The DataFrame is highly fragmented*")

# --- Config ---
OANDA_INSTRUMENTS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]
GRANULARITY = "D"
N_BARS = 20000  # Default to 20,000 bars per instrument (or as much as available)
CHUNK_SIZE = 5000  # OANDA API max chunk size
DB_URL = "postgresql://postgres:password@localhost:5432/rl_forex"

# --- OANDA Pagination Helper ---
def fetch_all_candles(instrument, granularity, n_bars):
    all_dfs = []
    fetched = 0
    max_per_req = 5000
    to_time = None
    # Start from the latest timestamp in DB, or now if none
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT MIN(timestamp) FROM candles_wide WHERE instrument = :instrument AND granularity = :granularity
            """), {"instrument": instrument, "granularity": granularity}
        )
        row = result.fetchone()
        if row and row[0]:
            to_time = pd.to_datetime(row[0])
        else:
            to_time = pd.Timestamp.utcnow()
    while fetched < n_bars:
        count = min(max_per_req, n_bars - fetched)
        df = fetch_candles(instrument, granularity=granularity, count=count, to=to_time)
        try:
            if to_time is not None:
                df = df[df['timestamp'] < to_time]
        except KeyError:
            print(f"No 'timestamp' in returned data for {instrument}, likely reached earliest data.")
            break
        if df.empty:
            break
        to_time = df['timestamp'].min() - pd.Timedelta(seconds=1)
        all_dfs.append(df)
        fetched += len(df)
        if len(df) < count:
            break
        time.sleep(0.5)  # Be nice to the API
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return pd.DataFrame()

def add_time_features(df):
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Hour of day
    df['hour'] = df['timestamp'].dt.hour
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    # Day of week
    df['dow'] = df['timestamp'].dt.dayofweek
    df['dow_sin'] = np.sin(2 * np.pi * df['dow'] / 7)
    df['dow_cos'] = np.cos(2 * np.pi * df['dow'] / 7)
    # Week of month
    df['dom'] = df['timestamp'].dt.day
    df['wom'] = ((df['dom'] - 1) // 7) + 1
    df['wom_sin'] = np.sin(2 * np.pi * df['wom'] / 5)
    df['wom_cos'] = np.cos(2 * np.pi * df['wom'] / 5)
    # Month of year
    df['month'] = df['timestamp'].dt.month
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    return df

def fetch_and_process(instrument, n_bars):
    print(f"Fetching {n_bars} bars for {instrument}...")
    df = fetch_all_candles(instrument, GRANULARITY, n_bars)
    if df.empty:
        print(f"No data for {instrument}")
        return None
    print(f"Adding cyclical time features for {instrument}...")
    df = add_time_features(df)
    print(f"Calculating indicators for {instrument}...")
    df = add_indicators(df)
    df['instrument'] = instrument
    df['granularity'] = GRANULARITY
    df = df.copy()
    return df

def fetch_and_process_iterative(instrument, n_bars=N_BARS, chunk_size=CHUNK_SIZE):
    print(f"Iterative fetching for {instrument}, {n_bars} bars, chunk size {chunk_size}...")
    all_rows = 0
    to_time = None
    engine = create_engine(DB_URL)
    metadata = MetaData()
    candles_wide = Table('candles_wide', metadata, autoload_with=engine)
    # --- Resumption logic: get earliest timestamp for this instrument/granularity ---
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT MIN(timestamp) FROM candles_wide WHERE instrument = :instrument AND granularity = :granularity
            """), {"instrument": instrument, "granularity": GRANULARITY}
        )
        row = result.fetchone()
        if row and row[0]:
            to_time = pd.to_datetime(row[0])
            print(f"Backfilling {instrument} up to {to_time}...")
        else:
            to_time = pd.Timestamp.utcnow()
            print(f"No existing data for {instrument}, backfilling from now...")
    fetched = 0
    chunk_num = 0
    while fetched < n_bars:
        count = min(chunk_size, n_bars - fetched)
        df = fetch_candles(instrument, granularity=GRANULARITY, count=count, to=to_time)
        try:
            if to_time is not None:
                df = df[df['timestamp'] < to_time]
        except KeyError:
            print(f"No 'timestamp' in returned data for {instrument}, likely reached earliest data.")
            break
        if df.empty:
            print(f"No more data for {instrument} at chunk {chunk_num}.")
            break
        to_time = df['timestamp'].min() - pd.Timedelta(seconds=1)
        print(f"Chunk {chunk_num}: {len(df)} rows, {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Adding cyclical time features for {instrument} chunk {chunk_num}...")
        df = add_time_features(df)
        print(f"Calculating indicators for {instrument} chunk {chunk_num}...")
        df = add_indicators(df)
        df['instrument'] = instrument
        df['granularity'] = GRANULARITY
        df = df.copy()
        # Prepare for DB insert
        feature_cols = [col for col in df.columns if col not in ['timestamp', 'instrument', 'granularity']]
        insert_df = df[['timestamp', 'instrument', 'granularity']].copy()
        features_clean = df[feature_cols].replace([np.nan, np.inf, -np.inf], None)
        insert_df['features'] = features_clean.to_dict(orient='records')
        insert_df['features'] = insert_df['features'].apply(lambda x: json.dumps(x, allow_nan=False))
        records = insert_df.to_dict(orient='records')
        # Insert in DB in batches of 2,000
        for start in range(0, len(records), 2000):
            end = min(start + 2000, len(records))
            batch = records[start:end]
            print(f"Inserting {instrument} chunk {chunk_num} rows {start} to {end} into candles_wide...")
            with engine.begin() as conn:
                stmt = pg_insert(candles_wide).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp', 'instrument', 'granularity'])
                conn.execute(stmt)
            print(f"Batch {start} to {end} inserted for {instrument} chunk {chunk_num}.")
        fetched += len(df)
        chunk_num += 1
        all_rows += len(df)
        time.sleep(0.5)  # Be nice to the API
    print(f"Done ingesting {all_rows} rows for {instrument}.")

def main(test_mode=False):
    n_bars = 100 if test_mode else N_BARS
    instruments = OANDA_INSTRUMENTS[:2] if test_mode else OANDA_INSTRUMENTS
    print(f"Starting iterative ingestion for {len(instruments)} instruments, {n_bars} bars each.")
    for instrument in instruments:
        fetch_and_process_iterative(instrument, n_bars, chunk_size=2000)

def ingest_etf_data(etf_tickers, data_source, granularity="D"):
    """
    Ingest ETF OHLCV data for the given tickers from a specified data source (CSV or API).
    Calculates indicators and stores in the same DB schema as forex data.
    Args:
        etf_tickers (list): List of ETF ticker symbols (e.g., ['SPY', 'QQQ']).
        data_source (str or dict): Path to CSV(s) or API config for fetching ETF data.
        granularity (str): Data frequency, default 'D' for daily.
    """
    # TODO: Implement ETF data loading (from CSV or API)
    # Example: Use pandas.read_csv or yfinance to fetch OHLCV
    # For each ETF, load data, add indicators, and ingest to DB
    raise NotImplementedError("ETF ingestion not yet implemented. Awaiting further instruction.")

def ingest_etf_csvs(etf_dir, granularity="D"): 
    """
    Ingest all ETF daily CSVs in the given directory into the database with rich features.
    Args:
        etf_dir (str): Path to directory containing *_daily_*.csv files.
        granularity (str): Data frequency, default 'D' for daily.
    """
    csv_files = glob.glob(os.path.join(etf_dir, '*_daily_*.csv'))
    print(f"Found {len(csv_files)} ETF daily CSV files in {etf_dir}")
    engine = create_engine(DB_URL)
    metadata = MetaData()
    candles_wide = Table('candles_wide', metadata, autoload_with=engine)
    for csv_path in csv_files:
        instrument = os.path.basename(csv_path).split('_daily_')[0]
        print(f"Processing {instrument} from {csv_path}")
        df = pd.read_csv(csv_path)
        # Remove non-numeric second row if present
        if pd.isna(pd.to_datetime(df.iloc[0,0], errors='coerce')):
            df = df.iloc[1:].reset_index(drop=True)
        # Standardize column names
        col_map = {c.lower().replace(' ', '').replace('adjclose', 'adj_close'): c for c in df.columns}
        # Map to expected names
        df_std = pd.DataFrame()
        df_std['timestamp'] = pd.to_datetime(df[col_map.get('timestamp', 'timestamp')])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_std[col] = pd.to_numeric(df[col_map.get(col, col.capitalize())], errors='coerce')
        df_std['instrument'] = instrument
        df_std['granularity'] = granularity
        # Prepare for DB insert
        feature_cols = [col for col in df_std.columns if col not in ['timestamp', 'instrument', 'granularity']]
        insert_df = df_std[['timestamp', 'instrument', 'granularity']].copy()
        features_clean = df_std[feature_cols].replace([np.nan, np.inf, -np.inf], None)
        insert_df['features'] = features_clean.to_dict(orient='records')
        insert_df['features'] = insert_df['features'].apply(lambda x: json.dumps(x, allow_nan=False))
        records = insert_df.to_dict(orient='records')
        # Insert in DB in batches
        for start in range(0, len(records), 2000):
            end = min(start + 2000, len(records))
            batch = records[start:end]
            print(f"Inserting {instrument} rows {start} to {end} into candles_wide...")
            with engine.begin() as conn:
                stmt = pg_insert(candles_wide).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp', 'instrument', 'granularity'])
                conn.execute(stmt)
            print(f"Batch {start} to {end} inserted for {instrument}.")
    print("ETF CSV ingestion complete.")

def ingest_raw_oanda_data():
    """
    Fetch and ingest only raw price, volume, and spread data for all OANDA instruments.
    No indicators/features are calculated at this stage.
    """
    engine = create_engine(DB_URL)
    metadata = MetaData()
    candles_wide = Table('candles_wide', metadata, autoload_with=engine)
    for instrument in OANDA_INSTRUMENTS:
        print(f"Fetching raw data for {instrument}...")
        df = fetch_all_candles(instrument, granularity=GRANULARITY, n_bars=20000)
        if df is None or df.empty:
            print(f"No data for {instrument}")
            continue
        # Only keep raw columns
        raw_cols = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'bid_open', 'bid_high', 'bid_low', 'bid_close',
            'ask_open', 'ask_high', 'ask_low', 'ask_close',
            'spread', 'tick_volume'
        ]
        for col in raw_cols:
            if col not in df.columns:
                df[col] = None
        df = df[raw_cols]
        # Build features dict per row
        records = []
        for _, row in df.iterrows():
            features = {col: row[col] for col in raw_cols if col != 'timestamp'}
            records.append({
                'timestamp': row['timestamp'],
                'instrument': instrument,
                'granularity': GRANULARITY,
                'features': json.dumps(features, allow_nan=False)
            })
        # Insert in DB in batches
        for start in range(0, len(records), 2000):
            end = min(start + 2000, len(records))
            batch = records[start:end]
            with engine.begin() as conn:
                stmt = pg_insert(candles_wide).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp', 'instrument', 'granularity'])
                conn.execute(stmt)
        print(f"Raw OANDA data for {instrument} ingested.")

def ingest_raw_etf_csvs(etf_dir):
    """
    Ingest only raw price/volume data from ETF CSVs (no indicators/features).
    """
    import glob
    import os
    engine = create_engine(DB_URL)
    metadata = MetaData()
    candles_wide = Table('candles_wide', metadata, autoload_with=engine)
    csv_files = glob.glob(os.path.join(etf_dir, '*_daily_*.csv'))
    for csv_path in csv_files:
        instrument = os.path.basename(csv_path).split('_')[0]
        print(f"Ingesting raw ETF data for {instrument} from {csv_path}...")
        df = pd.read_csv(csv_path)
        # Remove non-numeric second row if present
        if pd.isna(pd.to_datetime(df.iloc[0,0], errors='coerce')):
            df = df.iloc[1:].reset_index(drop=True)
        # Standardize column names
        col_map = {c.lower().replace(' ', '').replace('adjclose', 'adj_close'): c for c in df.columns}
        # Map to expected names
        df_std = pd.DataFrame()
        df_std['timestamp'] = pd.to_datetime(df[col_map.get('timestamp', 'timestamp')])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_std[col] = pd.to_numeric(df[col_map.get(col, col.capitalize())], errors='coerce')
        # Build features dict per row
        raw_cols = ['open', 'high', 'low', 'close', 'volume']
        records = []
        for _, row in df_std.iterrows():
            features = {col: row[col] for col in raw_cols}
            records.append({
                'timestamp': row['timestamp'],
                'instrument': instrument,
                'granularity': GRANULARITY,
                'features': json.dumps(features, allow_nan=False)
            })
        # Insert in DB in batches
        for start in range(0, len(records), 2000):
            end = min(start + 2000, len(records))
            batch = records[start:end]
            with engine.begin() as conn:
                stmt = pg_insert(candles_wide).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp', 'instrument', 'granularity'])
                conn.execute(stmt)
        print(f"Raw ETF data for {instrument} ingested.")

def verify_raw_data(instrument, granularity="D", min_rows=1000):
    """
    Verify that raw data for a given instrument/granularity is present and valid (not all null, enough rows).
    """
    from sqlalchemy import create_engine, text
    engine = create_engine(DB_URL)
    raw_cols = [
        'open', 'high', 'low', 'close', 'volume',
        'bid_open', 'bid_high', 'bid_low', 'bid_close',
        'ask_open', 'ask_high', 'ask_low', 'ask_close',
        'spread', 'tick_volume'
    ]
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM candles_wide WHERE instrument = :instrument AND granularity = :granularity
        """), {"instrument": instrument, "granularity": granularity})
        n_rows = result.scalar()
        print(f"{instrument} ({granularity}): {n_rows} rows")
        if n_rows < min_rows:
            print(f"WARNING: Only {n_rows} rows for {instrument} {granularity}")
        # Check nulls for each column
        for col in raw_cols:
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM candles_wide WHERE instrument = :instrument AND granularity = :granularity AND ({col} IS NULL)
            """), {"instrument": instrument, "granularity": granularity})
            n_null = result.scalar()
            pct_null = 100.0 * n_null / max(n_rows, 1)
            print(f"  {col:12s}: {pct_null:6.2f}% null")
        print("---")

def add_features_to_existing_rows(instrument, granularity="D"):
    """
    Compute and add features/indicators to existing raw data rows for a given instrument/granularity.
    """
    from sqlalchemy import create_engine, text
    from rl.data.indicators import add_indicators
    engine = create_engine(DB_URL)
    # Fetch all rows for this instrument/granularity
    df = pd.read_sql(text(f"""
        SELECT * FROM candles_wide WHERE instrument = :instrument AND granularity = :granularity
    """), engine, params={"instrument": instrument, "granularity": granularity})
    if df.empty:
        print(f"No data for {instrument} {granularity}")
        return
    # Calculate features/indicators
    df_feat = add_indicators(df.copy())
    # Update features column in DB
    with engine.begin() as conn:
        for idx, row in df_feat.iterrows():
            features = row.get('features', None)
            ts = row['timestamp']
            conn.execute(text(f"""
                UPDATE candles_wide SET features = :features WHERE instrument = :instrument AND granularity = :granularity AND timestamp = :timestamp
            """), {
                "features": features,
                "instrument": instrument,
                "granularity": granularity,
                "timestamp": ts
            })
    print(f"Features added for {instrument} {granularity}")

# CLI entry points for each stage
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest-raw-oanda", action="store_true", help="Ingest only raw OANDA data")
    parser.add_argument("--ingest-raw-etf-csvs", type=str, help="Ingest only raw ETF CSVs from directory")
    parser.add_argument("--verify-raw", type=str, help="Verify raw data for instrument (e.g. EUR_USD)")
    parser.add_argument("--add-features", type=str, help="Add features to existing rows for instrument (e.g. EUR_USD)")
    args = parser.parse_args()
    if args.ingest_raw_oanda:
        ingest_raw_oanda_data()
    if args.ingest_raw_etf_csvs:
        ingest_raw_etf_csvs(args.ingest_raw_etf_csvs)
    if args.verify_raw:
        verify_raw_data(args.verify_raw)
    if args.add_features:
        add_features_to_existing_rows(args.add_features) 