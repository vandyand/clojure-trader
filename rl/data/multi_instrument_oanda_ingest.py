import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from rl.data.fetch_oanda import fetch_candles
from rl.data.indicators import add_indicators
import time
from sqlalchemy.dialects.postgresql import JSONB
import numpy as np
import json
from sqlalchemy import Table, MetaData, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
import argparse

# --- Config ---
OANDA_INSTRUMENTS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]
GRANULARITY = "H1"
N_BARS = 20000  # Set to 100 for test mode
DB_URL = "postgresql://postgres:password@localhost:5432/rl_forex"

# --- OANDA Pagination Helper ---
def fetch_all_candles(instrument, granularity, n_bars):
    all_dfs = []
    fetched = 0
    max_per_req = 5000
    last_time = None
    while fetched < n_bars:
        count = min(max_per_req, n_bars - fetched)
        df = fetch_candles(instrument, granularity=granularity, count=count)
        if df.empty:
            break
        if last_time is not None:
            df = df[df['timestamp'] > last_time]
        if df.empty:
            break
        last_time = df['timestamp'].max()
        all_dfs.append(df)
        fetched += len(df)
        if len(df) < count:
            break
        time.sleep(0.5)  # Be nice to the API
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return pd.DataFrame()

def fetch_and_process(instrument, n_bars):
    print(f"Fetching {n_bars} bars for {instrument}...")
    df = fetch_all_candles(instrument, GRANULARITY, n_bars)
    if df.empty:
        print(f"No data for {instrument}")
        return None
    print(f"Calculating indicators for {instrument}...")
    df = add_indicators(df)
    df['instrument'] = instrument
    df['granularity'] = GRANULARITY
    # Defragment DataFrame after all columns are added
    df = df.copy()
    return df

def fetch_and_process_iterative(instrument, n_bars, chunk_size=2000):
    print(f"Iterative fetching for {instrument}, {n_bars} bars, chunk size {chunk_size}...")
    all_rows = 0
    last_time = None
    engine = create_engine(DB_URL)
    metadata = MetaData()
    candles_wide = Table('candles_wide', metadata, autoload_with=engine)
    fetched = 0
    chunk_num = 0
    while fetched < n_bars:
        count = min(chunk_size, n_bars - fetched)
        df = fetch_candles(instrument, granularity=GRANULARITY, count=count)
        if df.empty:
            print(f"No more data for {instrument} at chunk {chunk_num}.")
            break
        if last_time is not None:
            df = df[df['timestamp'] > last_time]
        if df.empty:
            print(f"No new data for {instrument} at chunk {chunk_num}.")
            break
        last_time = df['timestamp'].max()
        print(f"Chunk {chunk_num}: {len(df)} rows, {df['timestamp'].min()} to {df['timestamp'].max()}")
        df = add_indicators(df)
        df['instrument'] = instrument
        df['granularity'] = GRANULARITY
        df = df.copy()  # Defragment
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OANDA multi-instrument data ingestion.")
    parser.add_argument('--test', action='store_true', help='Run in test mode (small subset)')
    args = parser.parse_args()
    main(test_mode=args.test) 