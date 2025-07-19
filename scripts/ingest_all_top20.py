import pandas as pd
from trading_systems.rl.data.fetch_oanda import fetch_candles
from trading_systems.rl.data.indicators import add_indicators
from trading_systems.rl.data.ingest import ingest_candles

PAIRS = [
    'EUR_USD', 'USD_JPY', 'GBP_USD', 'AUD_USD', 'USD_CHF',
    'USD_CAD', 'NZD_USD', 'EUR_JPY', 'GBP_JPY', 'EUR_GBP',
    'EUR_CHF', 'EUR_AUD', 'EUR_CAD', 'GBP_CHF', 'AUD_JPY',
    'AUD_CHF', 'CAD_JPY', 'NZD_JPY', 'GBP_AUD', 'AUD_NZD'
]

def main():
    for pair in PAIRS:
        try:
            df = fetch_candles(pair, granularity='D', count=2000)
            if df.empty:
                print(f'No data for {pair}, skipping.')
                continue
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