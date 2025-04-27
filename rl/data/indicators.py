import pandas as pd
import ta
import numpy as np

# Fibonacci windows up to 500
LOOKBACK_WINDOWS = [2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
SAFE_MIN_PERIODS = 2

# Define all price series columns
PRICE_SERIES = [
    'open', 'high', 'low', 'close',
    'bid_open', 'bid_high', 'bid_low', 'bid_close',
    'ask_open', 'ask_high', 'ask_low', 'ask_close',
    'volume', 'spread'
]

# For bivariate indicators
BID_ASK_PAIRS = [
    ('bid_close', 'ask_close'),
    ('bid_open', 'ask_open'),
    ('bid_high', 'ask_high'),
    ('bid_low', 'ask_low'),
]
MID_BID_ASK_PAIRS = [
    ('mid_close', 'bid_close'),
    ('mid_close', 'ask_close'),
    ('mid_open', 'bid_open'),
    ('mid_open', 'ask_open'),
    ('mid_high', 'bid_high'),
    ('mid_high', 'ask_high'),
    ('mid_low', 'bid_low'),
    ('mid_low', 'ask_low'),
]

# Helper to get mid prices if not present
MID_COLS = ['mid_open', 'mid_high', 'mid_low', 'mid_close']


def add_indicators(df):
    df = df.copy()
    # Add mid prices if not present
    for ohlc in ['open', 'high', 'low', 'close']:
        mid_col = f'mid_{ohlc}'
        if mid_col not in df.columns:
            df[mid_col] = (df[f'bid_{ohlc}'] + df[f'ask_{ohlc}']) / 2

    # --- Univariate indicators for all series ---
    for col in PRICE_SERIES + MID_COLS:
        if col not in df.columns:
            continue
        for window in LOOKBACK_WINDOWS:
            # Moving averages
            df[f'{col}_sma_{window}'] = df[col].rolling(window, min_periods=SAFE_MIN_PERIODS).mean()
            df[f'{col}_ema_{window}'] = df[col].ewm(span=window, min_periods=SAFE_MIN_PERIODS).mean()
            # Volatility
            df[f'{col}_std_{window}'] = df[col].rolling(window, min_periods=SAFE_MIN_PERIODS).std()
            # Momentum
            df[f'{col}_roc_{window}'] = df[col].pct_change(periods=window)
            # Min/max
            df[f'{col}_roll_min_{window}'] = df[col].rolling(window, min_periods=SAFE_MIN_PERIODS).min()
            df[f'{col}_roll_max_{window}'] = df[col].rolling(window, min_periods=SAFE_MIN_PERIODS).max()
            # Bollinger Bands
            bbm = df[col].rolling(window, min_periods=SAFE_MIN_PERIODS).mean()
            bbs = df[col].rolling(window, min_periods=SAFE_MIN_PERIODS).std()
            df[f'{col}_bb_bbm_{window}'] = bbm
            df[f'{col}_bb_bbh_{window}'] = bbm + 2 * bbs
            df[f'{col}_bb_bbl_{window}'] = bbm - 2 * bbs
            # RSI (only for price-like series)
            if col in ['open', 'high', 'low', 'close', 'bid_open', 'bid_high', 'bid_low', 'bid_close', 'ask_open', 'ask_high', 'ask_low', 'ask_close', 'mid_open', 'mid_high', 'mid_low', 'mid_close']:
                try:
                    df[f'{col}_rsi_{window}'] = ta.momentum.rsi(df[col], window=window)
                except Exception:
                    pass
            # ATR, CCI, ADX, Williams %R (only for OHLC sets)
            if col in ['close', 'bid_close', 'ask_close', 'mid_close']:
                prefix = col.split('_')[0] if '_' in col else 'mid'
                h = f'{prefix}_high'
                l = f'{prefix}_low'
                c = col
                try:
                    df[f'{col}_atr_{window}'] = ta.volatility.average_true_range(df[h], df[l], df[c], window=window)
                except Exception:
                    pass
                try:
                    df[f'{col}_cci_{window}'] = ta.trend.cci(df[h], df[l], df[c], window=window)
                except Exception:
                    pass
                try:
                    df[f'{col}_adx_{window}'] = ta.trend.adx(df[h], df[l], df[c], window=window)
                except Exception:
                    pass
                try:
                    df[f'{col}_williams_r_{window}'] = ta.momentum.williams_r(df[h], df[l], df[c], lbp=window)
                except Exception:
                    pass
    # --- Volume-based indicators ---
    for window in LOOKBACK_WINDOWS:
        try:
            df[f'volume_obv_{window}'] = ta.volume.on_balance_volume(df['close'], df['volume']).rolling(window, min_periods=SAFE_MIN_PERIODS).mean()
        except Exception:
            pass
        try:
            df[f'volume_mfi_{window}'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window=window)
        except Exception:
            pass
        df[f'volume_rel_vol_{window}'] = df['volume'] / (df['volume'].rolling(window, min_periods=SAFE_MIN_PERIODS).mean() + 1e-8)
    # --- Spread-based indicators ---
    for window in LOOKBACK_WINDOWS:
        df[f'spread_mean_{window}'] = df['spread'].rolling(window, min_periods=SAFE_MIN_PERIODS).mean()
        df[f'spread_std_{window}'] = df['spread'].rolling(window, min_periods=SAFE_MIN_PERIODS).std()
        df[f'spread_rel_spread_{window}'] = df['spread'] / (df['close'] + 1e-8)
        df[f'spread_spike_{window}'] = (df['spread'] > 2 * df[f'spread_mean_{window}']).astype(float)
        df[f'vol_x_spread_{window}'] = (df['volume'] * df['spread']).rolling(window, min_periods=SAFE_MIN_PERIODS).mean()
        # Bollinger Bands for spread
        bbm = df['spread'].rolling(window, min_periods=SAFE_MIN_PERIODS).mean()
        bbs = df['spread'].rolling(window, min_periods=SAFE_MIN_PERIODS).std()
        df[f'spread_bb_bbm_{window}'] = bbm
        df[f'spread_bb_bbh_{window}'] = bbm + 2 * bbs
        df[f'spread_bb_bbl_{window}'] = bbm - 2 * bbs
    # --- Bivariate indicators ---
    # Bid-ask spreads
    for (bid_col, ask_col) in BID_ASK_PAIRS:
        df[f'{ask_col}_minus_{bid_col}'] = df[ask_col] - df[bid_col]
        df[f'{ask_col}_div_{bid_col}'] = df[ask_col] / (df[bid_col] + 1e-8)
    # Mid-bid/ask spreads
    for (mid_col, other_col) in MID_BID_ASK_PAIRS:
        if mid_col in df.columns and other_col in df.columns:
            df[f'{mid_col}_minus_{other_col}'] = df[mid_col] - df[other_col]
            df[f'{mid_col}_div_{other_col}'] = df[mid_col] / (df[other_col] + 1e-8)
    # High-low spreads for each price type
    for prefix in ['open', 'high', 'low', 'close', 'bid', 'ask', 'mid']:
        h = f'{prefix}_high'
        l = f'{prefix}_low'
        if h in df.columns and l in df.columns:
            df[f'{h}_minus_{l}'] = df[h] - df[l]
            df[f'{h}_div_{l}'] = df[h] / (df[l] + 1e-8)
    # Bid-ask bounce
    if 'ask_close' in df.columns and 'bid_close' in df.columns:
        df['bid_ask_bounce'] = (df['ask_close'] - df['bid_close']).diff()
    return df 