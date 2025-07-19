import oandapyV20
import oandapyV20.endpoints.instruments as instruments
from rl.config import OANDA_API_KEY, OANDA_API_URL
import pandas as pd

client = oandapyV20.API(access_token=OANDA_API_KEY, environment="practice")

def fetch_candles(instrument, granularity="H1", count=500, to=None):
    """
    Fetch candlestick data from OANDA for a given instrument and granularity.
    Supported granularities include 'S5', 'M1', 'M5', 'M15', 'H1', 'D' (daily), etc.
    For daily signals, use granularity='D'.
    Optionally fetch candles up to a specific end time (ISO8601 string or pandas.Timestamp) using 'to'.
    """
    params = {
        "granularity": granularity,
        "count": count,
        "price": "MBA"  # Fetch mid, bid, ask
    }
    if to is not None:
        if isinstance(to, pd.Timestamp):
            to = to.isoformat()
        params["to"] = to
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(r)
    candles = response["candles"]
    if not candles:
        return pd.DataFrame()
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
    if df.empty or 'timestamp' not in df.columns:
        return pd.DataFrame()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    # Ensure 'volume' column exists for indicator compatibility
    if 'volume' not in df.columns and 'tick_volume' in df.columns:
        df['volume'] = df['tick_volume']
    return df 