import pandas as pd
from trading_systems.rl.data.fetch_oanda import fetch_candles
from trading_systems.rl.data.indicators import add_indicators, LOOKBACK_WINDOWS
from trading_systems.rl.data.ingest import ingest_candles
from datetime import datetime, timedelta
import time

PAIRS = [
    'EUR_USD', 'USD_JPY', 'GBP_USD', 'AUD_USD', 'USD_CHF',
    'USD_CAD', 'NZD_USD', 'EUR_JPY', 'GBP_JPY', 'EUR_GBP',
    'EUR_CHF', 'EUR_AUD', 'EUR_CAD', 'GBP_CHF', 'AUD_JPY',
    'AUD_CHF', 'CAD_JPY', 'NZD_JPY', 'GBP_AUD', 'AUD_NZD'
]

CHUNK_SIZE = 5000

def fetch_all_history(pair, granularity='D'):
    all_chunks = []
    to_time = None  # None means fetch latest
    while True:
        df = fetch_candles(pair, granularity=granularity, count=CHUNK_SIZE, to=to_time)
        if df.empty:
            break
        all_chunks.append(df)
        earliest = df['timestamp'].min()
        print(f"Fetched {len(df)} rows for {pair} up to {earliest}")
        # Move to_time back by 1 day to avoid overlap
        to_time = (pd.to_datetime(earliest) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        if len(df) < CHUNK_SIZE:
            break
        time.sleep(0.5)  # Avoid rate limits
    if not all_chunks:
        return pd.DataFrame()
    full_df = pd.concat(all_chunks, ignore_index=True)
    full_df = full_df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return full_df

def main():
    for pair in PAIRS:
        try:
            df = fetch_all_history(pair, granularity='D')
            if df.empty:
                print(f'No data for {pair}, skipping.')
                continue
            print(f"Total rows fetched for {pair}: {len(df)}")
            df = add_indicators(df)
            nan_rate = df.isna().mean().mean()
            print(f'Pre-ingest NaN for {pair}: {nan_rate:.4f}')
            print(f'First 3 rows for {pair}:\n', df.head(3))
            print(f'Last 3 rows for {pair}:\n', df.tail(3))
            ingest_candles(df, pair, 'D')
            print(f'Ingested {len(df)} rows for {pair}.')
        except Exception as e:
            print(f'Error ingesting {pair}: {e}')

if __name__ == '__main__':
    main() 