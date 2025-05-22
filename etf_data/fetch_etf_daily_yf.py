import yfinance as yf
import pandas as pd

# ETF proxies to fetch (symbol: description)
etfs = {
    'GLD': 'SPDR Gold Trust',  # Gold proxy
    'USO': 'United States Oil Fund',  # Oil proxy
    'SPY': 'S&P 500 ETF',  # Economic indicator
    'TLT': 'iShares 20+ Year Treasury Bond ETF',  # Economic indicator
    'BND': 'Vanguard Total Bond Market ETF',  # Economic indicator
}

for symbol, desc in etfs.items():
    print(f"Fetching {desc} ({symbol}) daily candles from Yahoo Finance...")
    df = yf.download(symbol, interval='1d', auto_adjust=False, progress=False)
    if df.empty:
        print(f"No data returned for {symbol}.")
        continue
    df.reset_index(inplace=True)
    df.rename(columns={'Date': 'timestamp'}, inplace=True)
    csv_filename = f"{symbol}_daily_yf.csv"
    df.to_csv(csv_filename, index=False)
    print(f"Saved {len(df)} daily candles for {symbol} to {csv_filename}") 