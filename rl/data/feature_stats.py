import os
import pandas as pd
import numpy as np
import argparse
from sqlalchemy import create_engine

DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

def get_instruments(etf=False):
    forex = [
        "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
        "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
        "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
        "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
    ]
    if not etf:
        return forex
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        df = pd.read_sql(
            f"""
            SELECT DISTINCT instrument FROM candles_wide
            WHERE instrument NOT IN {tuple(forex)} AND granularity = 'D'
            ORDER BY instrument
            """, conn)
    return df['instrument'].tolist()

def get_selected_features(instrument, n_features=None):
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        sql = f"""
            SELECT feature_name FROM selected_features_per_instrument
            WHERE instrument = %s
            ORDER BY rank
        """
        df = pd.read_sql(sql, conn, params=(instrument,))
    if n_features:
        return df['feature_name'].tolist()[:n_features]
    return df['feature_name'].tolist()

def fetch_feature_data(instrument, features, n_rows=10000):
    # Extract from features JSONB
    select_sql = ',\n        '.join([f"features->>'{f}' AS \"{f}\"" for f in features])
    sql = f"""
        SELECT {select_sql}
        FROM candles_wide
        WHERE instrument = %s AND granularity = 'D'
        LIMIT {n_rows}
    """
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params=(instrument,))
    return df

def print_stats(df, instrument):
    print(f"\nInstrument: {instrument}")
    for col in df.columns:
        arr = pd.to_numeric(df[col], errors='coerce')
        pct_zero = (arr == 0).mean() * 100
        pct_nan = arr.isna().mean() * 100
        print(f"{col:30s} mean={arr.mean():.4f} std={arr.std():.4f} min={arr.min():.4f} max={arr.max():.4f} %zero={pct_zero:.1f} %NaN={pct_nan:.1f}")

def main():
    parser = argparse.ArgumentParser(description="Selected feature statistical analysis.")
    parser.add_argument('--instrument', type=str, help='Instrument to analyze (default: all)')
    parser.add_argument('--etf', action='store_true', help='Analyze ETFs instead of forex')
    parser.add_argument('--n_features', type=int, help='Number of features to analyze per instrument (default: all)')
    parser.add_argument('--n_rows', type=int, default=10000, help='Rows to sample (default: 10000)')
    args = parser.parse_args()
    instruments = [args.instrument] if args.instrument else get_instruments(etf=args.etf)
    for inst in instruments:
        features = get_selected_features(inst, n_features=args.n_features)
        if not features:
            print(f"No selected features for {inst}")
            continue
        df = fetch_feature_data(inst, features, n_rows=args.n_rows)
        print_stats(df, inst)

if __name__ == '__main__':
    main() 