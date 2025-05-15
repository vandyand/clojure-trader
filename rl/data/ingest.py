import pandas as pd
from rl.data.indicators import add_indicators, LOOKBACK_WINDOWS
from rl.db.models import Candle
from rl.db import SessionLocal
import logging
from sqlalchemy import create_engine, MetaData, Table
import json
from sqlalchemy import text
import math
import psycopg2
from typing import Dict, List
import argparse
import os

def sanitize_for_json(d):
    return {k: (v if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else None)
            for k, v in d.items()}

def ingest_candles(df, instrument, granularity):
    df = add_indicators(df, is_etf=False)
    # Drop first N rows where N = max rolling window (to avoid mostly-NaN features)
    max_window = max(LOOKBACK_WINDOWS)
    n_drop = max_window
    orig_len = len(df)
    df = df.iloc[n_drop:].reset_index(drop=True)
    print(f"Dropping first {n_drop} rows for {instrument} ({granularity}), {orig_len - len(df)} rows dropped.")
    session = SessionLocal()
    logging.basicConfig(level=logging.INFO)
    feature_cols = [col for col in df.columns if col not in {'timestamp', 'instrument', 'granularity', 'open', 'high', 'low', 'close', 'volume', 'bid_open', 'bid_high', 'bid_low', 'bid_close', 'ask_open', 'ask_high', 'ask_low', 'ask_close', 'spread', 'tick_volume'}]
    try:
        for i, (_, row) in enumerate(df.iterrows()):
            feature_kwargs = {f'feature_{j+1}': row.get(col) for j, col in enumerate(feature_cols)}
            candle = Candle(
                timestamp=row['timestamp'],
                instrument=instrument,
                granularity=granularity,
                open=row.get('open'),
                high=row.get('high'),
                low=row.get('low'),
                close=row.get('close'),
                volume=row.get('volume'),
                bid_open=row.get('bid_open'),
                bid_high=row.get('bid_high'),
                bid_low=row.get('bid_low'),
                bid_close=row.get('bid_close'),
                ask_open=row.get('ask_open'),
                ask_high=row.get('ask_high'),
                ask_low=row.get('ask_low'),
                ask_close=row.get('ask_close'),
                spread=row.get('spread'),
                tick_volume=row.get('tick_volume'),
                **feature_kwargs
            )
            session.merge(candle)  # Upsert
            if i % 1000 == 0:
                logging.info(f"Ingested {i} rows for {instrument} ({granularity})")
        session.commit()
        logging.info(f"Completed ingestion for {instrument} ({granularity})")
    finally:
        session.close()

def ingest_etf_candles(df, instrument, granularity):
    df = add_indicators(df, is_etf=True)
    # Only use OHLCV columns
    raw_cols = ['open', 'high', 'low', 'close', 'volume']
    df = df[raw_cols + ['timestamp']].copy()
    # Drop first N rows where N = max rolling window (to avoid mostly-NaN features)
    max_window = max(LOOKBACK_WINDOWS)
    n_drop = max_window
    orig_len = len(df)
    df = df.iloc[n_drop:].reset_index(drop=True)
    print(f"Dropping first {n_drop} rows for {instrument} ({granularity}), {orig_len - len(df)} rows dropped.")
    # Prepare feature columns (exclude raw and timestamp)
    feature_cols = [col for col in df.columns if col not in {'timestamp', 'open', 'high', 'low', 'close', 'volume'}]
    # Use all features from the grid (no slicing)
    # Insert into etf_candles
    engine = create_engine('postgresql://postgres:password@localhost:5432/rl_forex')
    metadata = MetaData()
    etf_candles = Table('etf_candles', metadata, autoload_with=engine)
    records = []
    for _, row in df.iterrows():
        record = {
            'timestamp': row['timestamp'],
            'instrument': instrument,
            'granularity': granularity,
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': row.get('close'),
            'volume': row.get('volume'),
        }
        for j, col in enumerate(feature_cols):
            record[f'feature_{j+1}'] = row.get(col)
        records.append(record)
    # Insert in batches
    with engine.begin() as conn:
        for start in range(0, len(records), 2000):
            end = min(start + 2000, len(records))
            batch = records[start:end]
            conn.execute(etf_candles.insert().values(batch))
    print(f"Ingested {len(df)} rows for {instrument} into etf_candles.")

def populate_forex_features(batch_size=1000):
    engine = create_engine('postgresql://postgres:password@localhost:5432/rl_forex')
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM forex_raw"))
        total = result.scalar()
        for offset in range(0, total, batch_size):
            df = pd.read_sql(f"SELECT * FROM forex_raw ORDER BY timestamp, instrument, granularity OFFSET {offset} LIMIT {batch_size}", conn)
            if df.empty:
                continue
            df_feat = add_indicators(df, is_etf=False)
            for idx, row in df_feat.iterrows():
                # Remove all-zero rows
                raw_vals = row[['open','high','low','close','bid_open','bid_high','bid_low','bid_close','ask_open','ask_high','ask_low','ask_close','volume','spread']].values
                if (raw_vals == 0).all():
                    continue
                features = {k: v for k, v in row.items() if k not in df.columns and pd.notnull(v)}
                insert = text("""
                    INSERT INTO forex_features (timestamp, instrument, granularity, features)
                    VALUES (:timestamp, :instrument, :granularity, :features)
                    ON CONFLICT (timestamp, instrument, granularity) DO UPDATE SET features=EXCLUDED.features
                """)
                conn.execute(insert, {
                    'timestamp': row['timestamp'],
                    'instrument': row['instrument'],
                    'granularity': row['granularity'],
                    'features': json.dumps(sanitize_for_json(features))
                })
            print(f"Inserted batch {offset} to {offset+batch_size} into forex_features.")

def populate_etf_features():
    engine = create_engine('postgresql://postgres:password@localhost:5432/rl_forex')
    target_etfs = get_etf_symbols_to_process()

    if not target_etfs:
        print("No target ETF symbols found to process for etf_features. Exiting.")
        return

    for instrument_symbol in target_etfs:
        print(f"\nProcessing features for ETF: {instrument_symbol}")
        with engine.connect() as conn:
            # Fetch all daily data for this instrument from etf_raw
            df_raw = pd.read_sql(
                text("SELECT * FROM etf_raw WHERE instrument = :instrument AND granularity = 'D' ORDER BY timestamp"),
                conn,
                params={'instrument': instrument_symbol}
            )

            if df_raw.empty:
                print(f"No raw data in etf_raw for {instrument_symbol} at 'D' granularity. Skipping.")
                continue

            # Ensure timestamp is datetime and make it timezone-naive (UTC base)
            df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'], utc=True).dt.tz_localize(None)
            df_raw.set_index('timestamp', inplace=True)
            
            # Ensure OHLCV columns are numeric for add_indicators
            for col in ['open', 'high', 'low', 'close', 'volume']:
                 if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
            df_raw.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True) # add_indicators needs non-NA here
            if df_raw.empty:
                print(f"Raw data for {instrument_symbol} became empty after NaN drop on OHLCV. Skipping.")
                    continue

            print(f"Raw data for {instrument_symbol} fetched: {df_raw.shape[0]} rows. Generating indicators...")
            # Call add_indicators. Pass a copy of df_raw to avoid modifying it if needed later.
            # The original df_raw.columns will be used to identify newly added feature columns.
            # original_raw_columns = list(df_raw.columns) # Capture before add_indicators modifies it
            df_feat = add_indicators(df_raw.copy(), is_etf=True) 
            print(f"Indicators generated for {instrument_symbol}. DataFrame shape: {df_feat.shape}")

            insert_count = 0
            # Iterate through each timestamp (row) in df_feat
            for timestamp, row_data in df_feat.iterrows():
                # Extract ALL columns from row_data (which includes original OHLCV and generated features)
                # after filtering for valid, non-infinite, non-NaN numerics.
                features_to_store = {k: v for k, v in row_data.items() 
                            if pd.notnull(v) and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))}
                
                if not features_to_store: # Skip if no valid features were generated/kept for this row
                    continue

                # Timestamp should be from the index of df_feat
                ts_to_insert = timestamp 
                if ts_to_insert.tzinfo is None: # Ensure UTC for DB
                     ts_to_insert = ts_to_insert.tz_localize('UTC')
                
                insert_stmt = text("""
                    INSERT INTO etf_features (timestamp, instrument, granularity, features)
                    VALUES (:timestamp, :instrument, :granularity, :features)
                    ON CONFLICT (timestamp, instrument, granularity) DO UPDATE SET features = EXCLUDED.features
                """)
                try:
                    conn.execute(insert_stmt, {
                        'timestamp': ts_to_insert,
                        'instrument': instrument_symbol,
                        'granularity': 'D',
                        'features': json.dumps(sanitize_for_json(features_to_store)) # sanitize_for_json should still be useful
                    })
                    insert_count += 1
                except Exception as e_ins:
                    print(f"Failed to insert features for {instrument_symbol} at {ts_to_insert}: {e_ins}")
                    # Decide on error handling: break, continue, or log & continue
                    break # Stop processing this instrument on first error for now
            
            if insert_count > 0:
                print(f"Committed {insert_count} feature rows for {instrument_symbol} to etf_features.")
            conn.commit() # Commit after each instrument is processed

    print("\nETF feature population process complete.")

def test_forex_features_pipeline(instrument="EUR_USD", batch_size=100):
    """Test the forex features pipeline on a small batch of data for one instrument."""
    print(f"=== Testing forex features pipeline for {instrument} with batch_size={batch_size} ===")
    engine = create_engine('postgresql://postgres:password@localhost:5432/rl_forex')
    with engine.begin() as conn:
        # Count total rows for this instrument
        result = conn.execute(text(f"SELECT COUNT(*) FROM forex_raw WHERE instrument = '{instrument}'"))
        total = result.scalar()
        print(f"Total rows for {instrument} in forex_raw: {total}")
        
        # Process a small batch
        query = f"""
            SELECT * FROM forex_raw 
            WHERE instrument = '{instrument}' AND granularity = 'D'
            ORDER BY timestamp
            LIMIT {batch_size}
        """
        print(f"Executing query: {query}")
        df = pd.read_sql(query, conn)
        print(f"Retrieved {len(df)} rows")
        
        if df.empty:
            print(f"No data found for {instrument}")
            return
            
        # Print raw data sample
        print("\nRaw data sample:")
        print(df.head(1))
        
        # Generate features
        print("\nGenerating features...")
        df_feat = add_indicators(df, is_etf=False)
        
        # Print feature columns generated
        feature_cols = [col for col in df_feat.columns if col not in df.columns]
        print(f"Generated {len(feature_cols)} feature columns")
        print(f"First 5 feature columns: {feature_cols[:5]}")
        
        # Show a few non-NaN feature values
        sample_features = {}
        for col in feature_cols[:10]:
            if not df_feat[col].isna().all():
                sample_features[col] = df_feat[col].iloc[0]
        print("\nSample feature values:")
        print(sample_features)
        
        # Test insertion
        print("\nTesting insertion...")
        for idx, row in df_feat.iloc[:5].iterrows():
            # Remove all-zero rows
            raw_vals = row[['open','high','low','close','bid_open','bid_high','bid_low','bid_close','ask_open','ask_high','ask_low','ask_close','volume','spread']].values
            if (raw_vals == 0).all():
                print(f"Row {idx} skipped: all raw_vals zero")
                continue
                
            features = {k: v for k, v in row.items() if k not in df.columns and pd.notnull(v)}
            print(f"Row {idx} has {len(features)} non-null features")
            
            # Sanitize values
            clean_features = sanitize_for_json(features)
            
            # Insert into forex_features
            insert = text("""
                INSERT INTO forex_features (timestamp, instrument, granularity, features)
                VALUES (:timestamp, :instrument, :granularity, :features)
                ON CONFLICT (timestamp, instrument, granularity) DO UPDATE SET features=EXCLUDED.features
            """)
            conn.execute(insert, {
                'timestamp': row['timestamp'],
                'instrument': row['instrument'],
                'granularity': row['granularity'],
                'features': json.dumps(clean_features)
            })
            print(f"Row {idx} inserted successfully")
            
        # Verify insertion
        count_query = text("SELECT COUNT(*) FROM forex_features WHERE instrument = :instrument")
        result = conn.execute(count_query, {'instrument': instrument})
        count = result.scalar()
        print(f"\nVerification: {count} rows for {instrument} in forex_features table")
        
        if count > 0:
            # Check one row
            sample_query = text("SELECT * FROM forex_features WHERE instrument = :instrument LIMIT 1")
            result = conn.execute(sample_query, {'instrument': instrument})
            row = result.fetchone()
            print(f"Sample row timestamp: {row[0]}, instrument: {row[1]}, granularity: {row[2]}")
            
            # Try to parse the features JSON
            if row and row[3]:  # Access features by index (3) not by name
                features_json = row[3]
                features_dict = json.loads(features_json) if isinstance(features_json, str) else features_json
                if isinstance(features_dict, dict):
                    print(f"Features JSON parsed successfully with {len(features_dict)} items")
                    # Show a sample of features (first 5 and last 5)
                    first_features = dict(list(features_dict.items())[:5])
                    print(f"First 5 features: {first_features}")
                else:
                    print(f"Features not a dictionary: {type(features_dict)}")
            else:
                print("No features found in row")
                
        print("=== Test complete ===") 

# Try to import constants, adjust path if necessary for standalone execution
try:
    from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
except ImportError:
    import sys
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.getenv('WORKSPACE_ROOT', os.path.dirname(script_dir)) # This should be the 'rl' directory
    #grandparent_dir = os.path.dirname(parent_dir) # This would be the workspace root
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    # Now try importing assuming the script is in rl/data and constants is in rl/
    from constants import PAIRS_BY_LIQUIDITY_OANDA

DB_NAME_INGEST = os.getenv('DB_NAME', 'rl_forex')
DB_USER_INGEST = os.getenv('DB_USER', 'postgres')
DB_PASSWORD_INGEST = os.getenv('DB_PASSWORD', 'password')
DB_HOST_INGEST = os.getenv('DB_HOST', 'localhost')
DB_PORT_INGEST = os.getenv('DB_PORT', '5432')

def get_conn_ingest(): # Renamed to avoid conflict if other get_conn exists
    return psycopg2.connect(dbname=DB_NAME_INGEST, user=DB_USER_INGEST, password=DB_PASSWORD_INGEST, host=DB_HOST_INGEST, port=DB_PORT_INGEST)

def get_all_instruments_from_selection_table() -> Dict[str, List[str]]:
    """Fetches all instruments and their currently selected features (used to derive ETF list)."""
    query = "SELECT instrument, feature_name FROM selected_features_per_instrument ORDER BY instrument, rank;"
    instrument_features: Dict[str, List[str]] = {}
    with get_conn_ingest() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            for row in cur:
                instrument, feature_name = row
                if instrument not in instrument_features:
                    instrument_features[instrument] = []
                instrument_features[instrument].append(feature_name) # Store all features for now
    return instrument_features

def get_etf_symbols_to_process() -> List[str]:
    """Derives ETF symbols from the full list of instruments in selected_features_per_instrument."""
    all_selected_instruments = get_all_instruments_from_selection_table()
    etf_symbols = []
    # PAIRS_BY_LIQUIDITY_OANDA should be imported correctly from rl.constants
    fx_pairs_set = set(PAIRS_BY_LIQUIDITY_OANDA)
    sorted_instruments = sorted(list(all_selected_instruments.keys())) 
    for inst in sorted_instruments:
        if inst not in fx_pairs_set:
            etf_symbols.append(inst)
    print(f"Derived {len(etf_symbols)} potential ETF symbols for feature generation. Will process up to 34.")
    return etf_symbols[:34] # Cap at 34 as per specification

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data Ingestion and Feature Population CLI")
    parser.add_argument("--populate-forex-features", action="store_true", help="Run populate_forex_features function.")
    parser.add_argument("--populate-etf-features", action="store_true", help="Run populate_etf_features function.")
    parser.add_argument("--test-forex-pipeline", action="store_true", help="Run test_forex_features_pipeline.")
    parser.add_argument("--instrument", type=str, default="EUR_USD", help="Instrument for testing pipeline.")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for testing pipeline.")

    args = parser.parse_args()

    if args.populate_forex_features:
        print("Running populate_forex_features...")
        populate_forex_features() # Assuming default batch size is handled within the function or it is removed
    elif args.populate_etf_features:
        print("Running populate_etf_features...")
        populate_etf_features()
    elif args.test_forex_pipeline:
        print(f"Running test_forex_features_pipeline for {args.instrument}...")
        test_forex_features_pipeline(instrument=args.instrument, batch_size=args.batch_size)
    else:
        print("No action specified. Use --populate-forex-features, --populate-etf-features, or --test-forex-pipeline.") 