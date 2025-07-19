from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.fetch_oanda import fetch_candles
from rl.data.ingest import ingest_candles

def main():
    granularity = "H1"
    for instrument in PAIRS_BY_LIQUIDITY_OANDA:
        print(f"Fetching {instrument}...")
        df = fetch_candles(instrument, granularity=granularity, count=5000)
        print(f"Fetched {len(df)} candles for {instrument}")
        ingest_candles(df, instrument, granularity)
        print(f"Ingested {instrument}")

if __name__ == "__main__":
    main() 