import pandas as pd
from rl.data.indicators import add_indicators
from rl.db.models import Candle
from rl.db import SessionLocal
import logging

def ingest_candles(df, instrument, granularity):
    df = add_indicators(df)
    session = SessionLocal()
    logging.basicConfig(level=logging.INFO)
    feature_cols = [col for col in df.columns if col not in {'timestamp', 'instrument', 'granularity', 'open', 'high', 'low', 'close', 'volume', 'bid_open', 'bid_high', 'bid_low', 'bid_close', 'ask_open', 'ask_high', 'ask_low', 'ask_close', 'spread', 'tick_volume'}]
    feature_cols = sorted(feature_cols)[:400]  # Use first 400 features alphabetically
    try:
        for i, (_, row) in enumerate(df.iterrows()):
            feature_kwargs = {f'feature_{j+1}': row.get(col) for j, col in enumerate(feature_cols)}
            candle = Candle(
                timestamp=row['timestamp'],
                instrument=instrument,
                granularity=granularity,
                open=row.get('open'),
                high=row.get('high'),
                low=row.get('low'),
                close=row.get('close'),
                volume=row.get('volume'),
                bid_open=row.get('bid_open'),
                bid_high=row.get('bid_high'),
                bid_low=row.get('bid_low'),
                bid_close=row.get('bid_close'),
                ask_open=row.get('ask_open'),
                ask_high=row.get('ask_high'),
                ask_low=row.get('ask_low'),
                ask_close=row.get('ask_close'),
                spread=row.get('spread'),
                tick_volume=row.get('tick_volume'),
                **feature_kwargs
            )
            session.merge(candle)  # Upsert
            if i % 1000 == 0:
                logging.info(f"Ingested {i} rows for {instrument} ({granularity})")
        session.commit()
        logging.info(f"Completed ingestion for {instrument} ({granularity})")
    finally:
        session.close() 