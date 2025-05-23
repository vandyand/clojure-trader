import sys
import os
# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitunix.client import BitUnixClient
from bitunix.models import Candlestick
from typing import List
import time # For potential timestamp conversions or logging

# This is a simple integration test script, not a formal unit test.
# It requires BITUNIX_API_KEY and BITUNIX_SECRET_KEY to be in the .env file
# in the root directory (or accessible to python-dotenv) if the client uses them,
# though for public kline data, they might not be strictly necessary for the request itself.

def main():
    print("Attempting to initialize BitUnixClient...")
    try:
        client = BitUnixClient()
        print("BitUnixClient initialized successfully.")
    except Exception as e:
        print(f"Error initializing BitUnixClient: {e}")
        return

    symbol = "BTCUSDT" # Example symbol
    interval = "1h"    # Example interval (1 hour)
    # Fetch a small number of recent klines
    limit = 5

    print(f"Fetching last {limit} klines for {symbol} at {interval} interval...")

    try:
        klines: List[Candlestick] = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        if klines:
            print(f"Successfully fetched {len(klines)} klines:")
            for k in klines:
                # Convert timestamp to readable format if desired
                # open_time_readable = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(k.open_time / 1000))
                print(
                    f"  Timestamp: {k.open_time}, "
                    # f"({open_time_readable} UTC), "
                    f"O: {k.open_price}, H: {k.high_price}, L: {k.low_price}, C: {k.close_price}, "
                    f"Vol: {k.volume}, QuoteVol: {k.quote_volume}, Type: {k.kline_type}"
                )
        else:
            print("No klines returned or an empty list was received.")

    except Exception as e:
        print(f"Error fetching klines: {e}")
        # If there was an HTTPError, the response text might be in e.response.text
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")

    # Test with specific time range
    print("\nTesting with specific time range...")
    # Get klines from 24 hours ago to now
    end_time = int(time.time() * 1000)  # Current time in ms
    start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago

    try:
        klines_range: List[Candlestick] = client.get_historical_klines(
            symbol=symbol,
            interval="15m",  # 15-minute intervals
            start_time=start_time,
            end_time=end_time,
            limit=10
        )
        if klines_range:
            print(f"Successfully fetched {len(klines_range)} kline(s) for the past 24 hours (15m intervals):")
            print(f"  First kline time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(klines_range[0].open_time/1000))} UTC")
            print(f"  Last kline time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(klines_range[-1].open_time/1000))} UTC")
        else:
            print("No klines returned for the specified time range.")
    except Exception as e:
        print(f"Error fetching klines with time range: {e}")

if __name__ == "__main__":
    # Create a .env file in the root of the 'trader' workspace (or ensure vars are set)
    # Example .env content:
    # BITUNIX_API_KEY=your_api_key_here
    # BITUNIX_SECRET_KEY=your_secret_key_here
    # For public kline data, these might not be used by the request if the API doesn't mandate them.
    main() 