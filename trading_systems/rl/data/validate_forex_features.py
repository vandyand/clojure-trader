import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import json

DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

def get_forex_instruments():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        df = pd.read_sql("""
            SELECT DISTINCT instrument FROM forex_features
            ORDER BY instrument
        """, conn)
    return df['instrument'].tolist()

def fetch_feature_data(instrument, n_rows=10000):
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        df = pd.read_sql(f"""
            SELECT * FROM forex_features
            WHERE instrument = '{instrument}'
            ORDER BY timestamp
            LIMIT {n_rows}
        """, conn)
    # Robustly handle features column as dict or string
    def parse_features(x):
        if isinstance(x, dict):
            return pd.Series(x)
        elif isinstance(x, str):
            return pd.Series(json.loads(x))
        else:
            return pd.Series({})
    features_df = df['features'].apply(parse_features)
    df = pd.concat([df.drop(columns=['features']), features_df], axis=1)
    return df

def print_stats(df, instrument):
    print(f"\nInstrument: {instrument}")
    for col in df.columns:
        arr = pd.to_numeric(df[col], errors='coerce')
        pct_zero = (arr == 0).mean() * 100
        pct_nan = arr.isna().mean() * 100
        print(f"{col:30s} mean={arr.mean():.4f} std={arr.std():.4f} min={arr.min():.4f} max={arr.max():.4f} %zero={pct_zero:.1f} %NaN={pct_nan:.1f}")

def main():
    instruments = get_forex_instruments()
    print(f"Found instruments: {instruments}")
    for inst in instruments:
        df = fetch_feature_data(inst, n_rows=10000)
        print(f"First 3 rows for {inst}:")
        print(df.head(3))
        print_stats(df, inst)

if __name__ == '__main__':
    main() 