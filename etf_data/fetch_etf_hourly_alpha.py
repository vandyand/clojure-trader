import os
import requests
import csv
import time

API_KEY = os.environ.get('ALPHAVANTAGE_API_KEY')
if not API_KEY:
    raise ValueError("ALPHAVANTAGE_API_KEY must be set as an environment variable.")

# ETF proxies to fetch (symbol: description)
etfs = {
    'GLD': 'SPDR Gold Trust',  # Gold proxy
    'USO': 'United States Oil Fund',  # Oil proxy
    'SPY': 'S&P 500 ETF',  # Economic indicator
    'TLT': 'iShares 20+ Year Treasury Bond ETF',  # Economic indicator
    'BND': 'Vanguard Total Bond Market ETF',  # Economic indicator
}

# Alpha Vantage intraday API details
BASE_URL = 'https://www.alphavantage.co/query'
INTERVAL = '60min'  # Hourly data
FUNCTION = 'TIME_SERIES_INTRADAY'
OUTPUTSIZE = 'full'  # Get as much data as allowed

for symbol, desc in etfs.items():
    params = {
        'function': FUNCTION,
        'symbol': symbol,
        'interval': INTERVAL,
        'apikey': API_KEY,
        'outputsize': OUTPUTSIZE,
        'datatype': 'json',
    }
    print(f"Fetching {desc} ({symbol})...")
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    if 'Time Series (60min)' not in data:
        print(f"No data returned for {symbol}. Response: {data}")
        continue
    timeseries = data['Time Series (60min)']
    # Write to CSV
    csv_filename = f"{symbol}_hourly_alpha.csv"
    with open(csv_filename, mode='w', newline='') as csvfile:
        fieldnames = ['timestamp'] + list(next(iter(timeseries.values())).keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for timestamp, values in sorted(timeseries.items()):
            row = {'timestamp': timestamp}
            row.update(values)
            writer.writerow(row)
    print(f"Saved {len(timeseries)} hourly candles for {symbol} to {csv_filename}")
    # Alpha Vantage free tier allows 5 requests per minute
    time.sleep(15) 