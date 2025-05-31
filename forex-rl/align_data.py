import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import time

def transform_database(db_path):
    """
    Transform database to have consistent timeline for all instruments
    with forward-filled price data and recalculated features
    """
    conn = sqlite3.connect(db_path)
    
    print("🔄 Starting database transformation...")
    start_time = time.time()
    
    # Get list of instruments
    instruments = [row[0] for row in conn.execute("SELECT DISTINCT instrument FROM candles").fetchall()]
    print(f"Found {len(instruments)} instruments")
    
    # Create master timeline (2007-10-14 to yesterday)
    min_time = pd.Timestamp('2007-10-14')
    max_time = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    full_timeline = pd.date_range(min_time, max_time, freq='D', name='time')
    print(f"📅 Created master timeline: {min_time.date()} to {max_time.date()}")

    # Load raw candles and convert times
    candles_df = pd.read_sql("SELECT * FROM candles", conn)
    candles_df['time'] = pd.to_datetime(candles_df['time'])
    candles_df['time'] = candles_df['time'].dt.tz_localize(None)  # Remove timezone
    candles_df['time'] = candles_df['time'].dt.normalize()  # Set to midnight

    # Process each instrument
    aligned_all = []
    
    for idx, instrument in enumerate(instruments):
        print(f"🔧 Processing {instrument} ({idx+1}/{len(instruments)})")
        
        # Filter to instrument
        df = candles_df[candles_df['instrument'] == instrument].copy()
        
        # Create full timeline DF
        instrument_df = pd.DataFrame({'time': full_timeline})
        
        # Merge with instrument data
        merged = instrument_df.merge(df, on='time', how='left')
        merged['instrument'] = merged['instrument'].fillna(instrument)
        
        # Forward fill prices
        ohlc_cols = ['open','high','low','close']
        merged[ohlc_cols] = merged[ohlc_cols].ffill()
        merged['volume'] = merged['volume'].fillna(0)
        
        aligned_all.append(merged)

    # Combine all instruments
    aligned_candles = pd.concat(aligned_all)
    
    # Calculate features
    fib_periods = [1,2,3,5,8,13,21,34,55,89,144,233,377,610,987]
    aligned_features = aligned_candles.copy()
    
    for period in fib_periods:
        print(f"   Calculating {period}-day Fibonacci features...")
        # Calculate separately for each instrument
        feat_dfs = []
        for inst in instruments:
            inst_df = aligned_features[aligned_features['instrument'] == inst].copy()
            inst_df[f'feat_{period}'] = np.log(inst_df['close'] / inst_df['close'].shift(period))
            feat_dfs.append(inst_df)
        aligned_features = pd.concat(feat_dfs)
    
    # Save to database
    print("💾 Saving transformed data...")
    aligned_candles.to_sql('aligned_candles', conn, if_exists='replace', index=False)
    aligned_features.to_sql('aligned_features', conn, if_exists='replace', index=False)
    
    # Create indexes
    for col in ['time', 'instrument']:
        conn.execute(f"CREATE INDEX idx_candles_{col} ON aligned_candles({col})")
        conn.execute(f"CREATE INDEX idx_features_{col} ON aligned_features({col})")
    
    conn.close()
    duration = time.time() - start_time
    print(f"✅ Transformation complete! Took {duration:.2f} seconds")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("Usage: python align_data.py <sqlite_db_path>")
    transform_database(sys.argv[1])
