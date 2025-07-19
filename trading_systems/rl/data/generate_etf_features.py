#!/usr/bin/env python
import os
import psycopg2
import pandas as pd
import numpy as np
import pandas_ta as ta # Using pandas_ta for a wide range of features
from typing import List, Dict, Optional
import json
import re

# Assuming rl.constants and db connection are accessible as in autoencoder_fusion
# If this script is run directly, sys.path might need adjustment for parent `rl` module
try:
    from rl.constants import PAIRS_BY_LIQUIDITY_OANDA # To help identify non-ETF instruments
except ImportError:
    # Fallback for direct execution or if constants are not strictly needed here beyond getting ETF list
    PAIRS_BY_LIQUIDITY_OANDA = [] 


DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

NEW_FEATURES_TABLE_NAME = "etf_features_all_generated"

def get_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def get_etf_symbols(all_selected_instruments: Dict[str, List[str]]) -> List[str]:
    """Derives ETF symbols from the full list of instruments in selected_features_per_instrument."""
    etf_symbols = []
    # Sort for consistent processing order, though not strictly necessary here
    sorted_instruments = sorted(list(all_selected_instruments.keys())) 
    for inst in sorted_instruments:
        if inst not in PAIRS_BY_LIQUIDITY_OANDA: # Crude way to filter, assumes PAIRS are comprehensive FX list
            etf_symbols.append(inst)
    # If PAIRS_BY_LIQUIDITY_OANDA is not exhaustive or reliable,
    # a more direct list of ETFs might be needed.
    # For now, assuming this gets the 34 ETFs.
    print(f"Derived {len(etf_symbols)} ETF symbols. First 5: {etf_symbols[:5]}")
    return etf_symbols[:34] # Cap at 34 as per prior discussions

def get_all_instruments_from_selection_table() -> Dict[str, List[str]]:
    """Fetches all instruments and their currently selected features (though features not used here)."""
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


def fetch_raw_etf_data(instrument_symbol: str, granularity: str = 'D') -> Optional[pd.DataFrame]:
    """Fetches raw OHLCV data for a given ETF symbol and granularity."""
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM etf_raw
        WHERE instrument = %s AND granularity = %s
        ORDER BY timestamp ASC;
    """
    try:
        with get_conn() as conn:
            df = pd.read_sql_query(query, conn, params=(instrument_symbol, granularity))
        if df.empty:
            print(f"No raw data found for {instrument_symbol} at {granularity} granularity.")
            return None
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
        df.set_index('timestamp', inplace=True)
        
        # Ensure correct dtypes for pandas_ta
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True) # Critical for TA lib
        
        print(f"Fetched raw data for {instrument_symbol}: {df.shape[0]} rows.")
        return df
    except Exception as e:
        print(f"Error fetching raw data for {instrument_symbol}: {e}")
        return None

def generate_features(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Generates a rich set of features using pandas_ta."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    print(f"Generating features for DataFrame with shape: {df_raw.shape}")
    
    # Ensure there are no NaN values in OHLCV data before calling pandas_ta
    # This is crucial as pandas_ta functions can fail with NaN values
    df = df_raw.copy()
    
    # Check for NaN values in required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    nan_counts = {col: df[col].isna().sum() for col in required_cols if col in df.columns}
    
    if any(count > 0 for count in nan_counts.values()):
        print(f"Warning: NaN values detected in OHLCV data: {nan_counts}")
        # Fill NaN values using forward fill then backward fill
        df[required_cols] = df[required_cols].ffill().bfill()
        
        # If there are still NaNs (e.g., at the beginning), replace with zeros
        df[required_cols] = df[required_cols].fillna(0)
        
        print("NaN values have been handled.")
    
    # Handle any inf values
    inf_mask = np.isinf(df[required_cols].values)
    if np.any(inf_mask):
        print("Warning: Infinite values detected in OHLCV data. Replacing with appropriate values.")
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df[required_cols] = df[required_cols].fillna(0)
    
    try:
        # Add technical indicators using pandas_ta
        # Momentum
        df.ta.rsi(length=14, append=True)
        df.ta.rsi(length=21, append=True)
        df.ta.stoch(k=14, d=3, smooth_k=3, append=True) # Adds STOCHk_14_3_3, STOCHd_14_3_3
        df.ta.cci(length=20, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True) # Adds MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        df.ta.roc(length=10, append=True)
        df.ta.williams(length=14, append=True) # Williams %R

        # Trend
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.adx(length=14, append=True) # ADX_14, DMP_14, DMN_14
        df.ta.psar(append=True) # PSARl_0.02_0.2, PSARs_0.02_0.2, PSARaf_0.02_0.2, PSARr_0.02_0.2

        # Volatility
        df.ta.atr(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True) # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
        
        # Volume (careful if volume data is not reliable for all ETFs)
        df.ta.obv(append=True)
        df.ta.mfi(length=14, append=True)
        
        # Other common ones
        df.ta.log_return(cumulative=False, append=True, col="LOGRET_1") # Log return
        df.ta.percent_return(cumulative=False, append=True, col="PCTRET_1")
    
    except Exception as e:
        print(f"Error calculating technical indicators: {str(e)}")
        print("Attempting to continue with partial feature set...")
    
    # Identify columns that were added (i.e., not original ohlcv or timestamp index)
    original_cols = {'open', 'high', 'low', 'close', 'volume'}
    feature_cols = [col for col in df.columns if col not in original_cols]
    features_df = df[feature_cols]
    
    # Replace potential +/- infinity with NaN, then fill NaNs
    features_df = features_df.replace([np.inf, -np.inf], np.nan)
    features_df = features_df.ffill().bfill().fillna(0)

    print(f"Generated {features_df.shape[1]} feature columns.")
    return features_df

def create_features_table_if_not_exists(conn):
    """Creates the NEW_FEATURES_TABLE_NAME if it doesn't exist."""
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {NEW_FEATURES_TABLE_NAME} (
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
    print(f"Ensured table {NEW_FEATURES_TABLE_NAME} exists.")

def insert_features_to_db(conn, instrument_symbol: str, granularity: str, features_df: pd.DataFrame):
    """Inserts the generated features (as JSONB) into the database."""
    if features_df.empty:
        print(f"No features to insert for {instrument_symbol}.")
        return

    print(f"Inserting {features_df.shape[0]} rows of features for {instrument_symbol} into {NEW_FEATURES_TABLE_NAME}...")
    
    # Iterate over each row (timestamp) in the features_df
    # In practice, for bulk inserts, psycopg2's execute_values or copy_expert would be much faster.
    # This row-by-row insert is for clarity and simplicity in this draft.
    
    insert_sql = f"""
    INSERT INTO {NEW_FEATURES_TABLE_NAME} (timestamp, instrument, granularity, features)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (timestamp, instrument, granularity) DO UPDATE SET features = EXCLUDED.features;
    """
    
    with conn.cursor() as cur:
        for timestamp, feature_values in features_df.iterrows():
            # Convert timestamp back to a suitable format if it was localized/delocalized
            # psycopg2 can handle pandas Timestamps directly if they are timezone-naive or UTC.
            # If 'timestamp' is index, use timestamp.tz_localize('UTC') if it's naive and DB expects tz-aware
            
            # Ensure timestamp is timezone-aware for PostgreSQL 'TIMESTAMP WITH TIME ZONE'
            # If timestamp from DataFrame index is naive, assume UTC.
            ts_to_insert = timestamp
            if ts_to_insert.tzinfo is None:
                ts_to_insert = ts_to_insert.tz_localize('UTC')
            
            # Convert the row of features to a JSON string
            features_json = json.dumps(feature_values.astype(float).to_dict()) # Ensure float for JSON compatibility
            try:
                cur.execute(insert_sql, (ts_to_insert, instrument_symbol, granularity, features_json))
            except Exception as e_insert:
                print(f"Error inserting for {instrument_symbol} at {ts_to_insert}: {e_insert}")
                print(f"Feature values sample: {feature_values.head().to_dict()}")
                # Optionally, skip this row or raise further
                conn.rollback() # Rollback this specific transaction
                break # Stop processing this instrument on first error
            
    conn.commit()
    print(f"Finished inserting features for {instrument_symbol}.")


def main():
    all_current_selections = get_all_instruments_from_selection_table()
    etf_symbols_to_process = get_etf_symbols(all_current_selections)
    
    if not etf_symbols_to_process:
        print("No ETF symbols identified for processing. Exiting.")
        return

    with get_conn() as conn_main: # Keep one connection for DDL and pass for DML
        create_features_table_if_not_exists(conn_main)

        for symbol in etf_symbols_to_process:
            print(f"\nProcessing ETF: {symbol}...")
            df_raw_etf = fetch_raw_etf_data(symbol, granularity='D')
            
            if df_raw_etf is None or df_raw_etf.empty:
                print(f"Skipping feature generation for {symbol} due to missing raw data.")
                continue
            
            df_features = generate_features(df_raw_etf)
            
            if df_features.empty:
                print(f"No features generated for {symbol}. Skipping database insert.")
                continue
            
            insert_features_to_db(conn_main, symbol, 'D', df_features)
            
    print("\nETF feature generation process complete.")
    print(f"All generated features are stored in table: '{NEW_FEATURES_TABLE_NAME}'.")
    print("Next steps: Perform feature selection on this table and then populate the final 'etf_features' table.")

if __name__ == "__main__":
    # Adjust sys.path if running this script directly from rl/data/ to import from parent rl.
    # import sys
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # parent_dir = os.path.dirname(script_dir)
    # if parent_dir not in sys.path:
    #     sys.path.append(parent_dir)
    # This helps if you try `python generate_etf_features.py` from within rl/data
    # If running as `python -m rl.data.generate_etf_features`, imports should work.

    main() 