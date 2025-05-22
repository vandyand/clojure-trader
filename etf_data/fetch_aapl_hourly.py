import os
import csv
from pyrh import Robinhood

# Load credentials from environment variables
username = os.environ.get('ROBINHOOD_USERNAME')
password = os.environ.get('ROBINHOOD_PASSWORD')

if not username or not password:
    raise ValueError("ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD must be set as environment variables.")

# Authenticate with Robinhood
rh = Robinhood(username=username, password=password)
rh.login()

# Fetch one year's worth of hourly historical data for AAPL
symbol = "AAPL"
interval = "hour"
span = "year"

data = rh.get_historical_quotes(symbol, interval, span)

# The data is expected to be in data['results'][0]['historicals']
historicals = data.get('results', [{}])[0].get('historicals', [])

if not historicals:
    raise RuntimeError("No historical data returned for AAPL.")

# Output to CSV
csv_filename = "aapl_hourly_candles.csv"
with open(csv_filename, mode='w', newline='') as csvfile:
    if historicals:
        fieldnames = list(historicals[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in historicals:
            writer.writerow(row)

print(f"Saved {len(historicals)} hourly candles for AAPL to {csv_filename}") 