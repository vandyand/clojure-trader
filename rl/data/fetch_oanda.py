import oandapyV20
import oandapyV20.endpoints.instruments as instruments
from rl.config import OANDA_API_KEY, OANDA_API_URL
import pandas as pd

client = oandapyV20.API(access_token=OANDA_API_KEY, environment="practice")

def fetch_candles(instrument, granularity="H1", count=500):
    params = {
        "granularity": granularity,
        "count": count,
        "price": "MBA"  # Fetch mid, bid, ask
    }
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)
    candles = response["candles"]
    data = []
    for c in candles:
        if not c["complete"]:
            continue
        mid = c.get("mid", {})
        bid = c.get("bid", {})
        ask = c.get("ask", {})
        data.append({
            "timestamp": c["time"],
            "open": float(mid.get("o", 'nan')),
            "high": float(mid.get("h", 'nan')),
            "low": float(mid.get("l", 'nan')),
            "close": float(mid.get("c", 'nan')),
            "bid_open": float(bid.get("o", 'nan')),
            "bid_high": float(bid.get("h", 'nan')),
            "bid_low": float(bid.get("l", 'nan')),
            "bid_close": float(bid.get("c", 'nan')),
            "ask_open": float(ask.get("o", 'nan')),
            "ask_high": float(ask.get("h", 'nan')),
            "ask_low": float(ask.get("l", 'nan')),
            "ask_close": float(ask.get("c", 'nan')),
            "spread": float(ask.get("c", 'nan')) - float(bid.get("c", 'nan')) if ("c" in ask and "c" in bid) else float('nan'),
            "volume": float(c.get("volume", 'nan'))
        })
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    # Ensure 'volume' column exists for indicator compatibility
    if 'volume' not in df.columns and 'tick_volume' in df.columns:
        df['volume'] = df['tick_volume']
    return df 