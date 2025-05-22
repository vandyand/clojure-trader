import pandas as pd
import ta
import numpy as np

# Fibonacci windows up to 500
LOOKBACK_WINDOWS = [2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
SAFE_MIN_PERIODS = 2

# Define all price series columns
PRICE_SERIES_FOREX = [
    'open', 'high', 'low', 'close',
    'bid_open', 'bid_high', 'bid_low', 'bid_close',
    'ask_open', 'ask_high', 'ask_low', 'ask_close',
    'volume', 'spread'
]
PRICE_SERIES_ETF = ['open', 'high', 'low', 'close', 'volume']

FEATURE_GRID = [
    # (feature_type, applicable_series, windows, extra_params)
    ('sma', None, LOOKBACK_WINDOWS, {}),
    ('ema', None, LOOKBACK_WINDOWS, {}),
    ('std', None, LOOKBACK_WINDOWS, {}),
    ('roc', None, LOOKBACK_WINDOWS, {}),
    ('roll_min', None, LOOKBACK_WINDOWS, {}),
    ('roll_max', None, LOOKBACK_WINDOWS, {}),
    ('bb_bbm', None, LOOKBACK_WINDOWS, {}),
    ('bb_bbh', None, LOOKBACK_WINDOWS, {}),
    ('bb_bbl', None, LOOKBACK_WINDOWS, {}),
    ('rsi', ['open', 'high', 'low', 'close', 'bid_open', 'bid_high', 'bid_low', 'bid_close', 'ask_open', 'ask_high', 'ask_low', 'ask_close', 'mid_open', 'mid_high', 'mid_low', 'mid_close'], LOOKBACK_WINDOWS, {}),
    ('atr', ['close', 'bid_close', 'ask_close', 'mid_close'], LOOKBACK_WINDOWS, {}),
    ('cci', ['close', 'bid_close', 'ask_close', 'mid_close'], LOOKBACK_WINDOWS, {}),
    ('adx', ['close', 'bid_close', 'ask_close', 'mid_close'], LOOKBACK_WINDOWS, {}),
    ('williams_r', ['close', 'bid_close', 'ask_close', 'mid_close'], LOOKBACK_WINDOWS, {}),
    # Volume-based
    ('obv', ['volume'], LOOKBACK_WINDOWS, {}),
    ('mfi', ['volume'], LOOKBACK_WINDOWS, {}),
    ('rel_vol', ['volume'], LOOKBACK_WINDOWS, {}),
    # Spread-based
    ('spread_mean', ['spread'], LOOKBACK_WINDOWS, {}),
    ('spread_std', ['spread'], LOOKBACK_WINDOWS, {}),
    ('spread_rel_spread', ['spread'], LOOKBACK_WINDOWS, {}),
    ('spread_spike', ['spread'], LOOKBACK_WINDOWS, {}),
    ('vol_x_spread', ['spread'], LOOKBACK_WINDOWS, {}),
    ('spread_bb_bbm', ['spread'], LOOKBACK_WINDOWS, {}),
    ('spread_bb_bbh', ['spread'], LOOKBACK_WINDOWS, {}),
    ('spread_bb_bbl', ['spread'], LOOKBACK_WINDOWS, {}),
]

# Registry of feature functions
FEATURE_FUNCS = {
    'sma': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean(),
    'ema': lambda s, w, df: df[s].ewm(span=w, min_periods=SAFE_MIN_PERIODS).mean(),
    'std': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).std(),
    'roc': lambda s, w, df: df[s].pct_change(periods=w),
    'roll_min': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).min(),
    'roll_max': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).max(),
    'bb_bbm': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean(),
    'bb_bbh': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean() + 2 * df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).std(),
    'bb_bbl': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean() - 2 * df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).std(),
    'rsi': lambda s, w, df: ta.momentum.rsi(df[s], window=w),
    'atr': lambda s, w, df: ta.volatility.average_true_range(df[f'{s.split("_")[0]}_high'], df[f'{s.split("_")[0]}_low'], df[s], window=w) if f'{s.split("_")[0]}_high' in df.columns and f'{s.split("_")[0]}_low' in df.columns else np.nan,
    'cci': lambda s, w, df: ta.trend.cci(df[f'{s.split("_")[0]}_high'], df[f'{s.split("_")[0]}_low'], df[s], window=w) if f'{s.split("_")[0]}_high' in df.columns and f'{s.split("_")[0]}_low' in df.columns else np.nan,
    'adx': lambda s, w, df: ta.trend.adx(df[f'{s.split("_")[0]}_high'], df[f'{s.split("_")[0]}_low'], df[s], window=w) if f'{s.split("_")[0]}_high' in df.columns and f'{s.split("_")[0]}_low' in df.columns else np.nan,
    'williams_r': lambda s, w, df: ta.momentum.williams_r(df[f'{s.split("_")[0]}_high'], df[f'{s.split("_")[0]}_low'], df[s], lbp=w) if f'{s.split("_")[0]}_high' in df.columns and f'{s.split("_")[0]}_low' in df.columns else np.nan,
    'obv': lambda s, w, df: ta.volume.on_balance_volume(df['close'], df['volume']).rolling(w, min_periods=SAFE_MIN_PERIODS).mean() if 'close' in df.columns and 'volume' in df.columns else np.nan,
    'mfi': lambda s, w, df: ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window=w) if all(x in df.columns for x in ['high','low','close','volume']) else np.nan,
    'rel_vol': lambda s, w, df: df['volume'] / (df['volume'].rolling(w, min_periods=SAFE_MIN_PERIODS).mean() + 1e-8) if 'volume' in df.columns else np.nan,
    'spread_mean': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean(),
    'spread_std': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).std(),
    'spread_rel_spread': lambda s, w, df: df[s] / (df['close'] + 1e-8) if 'close' in df.columns else np.nan,
    'spread_spike': lambda s, w, df: (df[s] > 2 * df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean()).astype(float),
    'vol_x_spread': lambda s, w, df: (df['volume'] * df[s]).rolling(w, min_periods=SAFE_MIN_PERIODS).mean() if 'volume' in df.columns else np.nan,
    'spread_bb_bbm': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean(),
    'spread_bb_bbh': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean() + 2 * df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).std(),
    'spread_bb_bbl': lambda s, w, df: df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).mean() - 2 * df[s].rolling(w, min_periods=SAFE_MIN_PERIODS).std(),
}

# Helper to get mid prices if not present
MID_COLS = ['mid_open', 'mid_high', 'mid_low', 'mid_close']

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

def add_indicators(df, is_etf=False):
    df = df.copy()
    # Add mid prices if not present and bid/ask columns exist (forex only)
    if not is_etf:
        for ohlc in ['open', 'high', 'low', 'close']:
            mid_col = f'mid_{ohlc}'
            bid_col = f'bid_{ohlc}'
            ask_col = f'ask_{ohlc}'
            if mid_col not in df.columns and bid_col in df.columns and ask_col in df.columns:
                df[mid_col] = (df[bid_col] + df[ask_col]) / 2
    # Choose base series
    base_series = PRICE_SERIES_ETF if is_etf else PRICE_SERIES_FOREX + MID_COLS
    # Systematic feature grid
    for feature_type, series_list, windows, params in FEATURE_GRID:
        # If series_list is None, use all base_series
        series_to_use = series_list if series_list is not None else base_series
        for s in series_to_use:
            if s not in df.columns:
                continue
            for w in windows:
                colname = f'{s}_{feature_type}_{w}'
                try:
                    df[colname] = FEATURE_FUNCS[feature_type](s, w, df)
                except Exception as e:
                    df[colname] = np.nan
    # --- Volume-based indicators ---
    if 'volume' in df.columns:
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
    if 'spread' in df.columns:
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
        if bid_col in df.columns and ask_col in df.columns:
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

if __name__ == "__main__":
    # Enumerate all unique feature names for forex and ETF
    def enumerate_features(is_etf):
        base_series = PRICE_SERIES_ETF if is_etf else PRICE_SERIES_FOREX + MID_COLS
        feature_names = set()
        for feature_type, series_list, windows, params in FEATURE_GRID:
            series_to_use = series_list if series_list is not None else base_series
            for s in series_to_use:
                for w in windows:
                    feature_names.add(f'{s}_{feature_type}_{w}')
        # Volume-based
        if not is_etf or 'volume' in PRICE_SERIES_ETF:
            for window in LOOKBACK_WINDOWS:
                feature_names.add(f'volume_obv_{window}')
                feature_names.add(f'volume_mfi_{window}')
                feature_names.add(f'volume_rel_vol_{window}')
        # Spread-based
        if not is_etf:
            for window in LOOKBACK_WINDOWS:
                feature_names.add(f'spread_mean_{window}')
                feature_names.add(f'spread_std_{window}')
                feature_names.add(f'spread_rel_spread_{window}')
                feature_names.add(f'spread_spike_{window}')
                feature_names.add(f'vol_x_spread_{window}')
                feature_names.add(f'spread_bb_bbm_{window}')
                feature_names.add(f'spread_bb_bbh_{window}')
                feature_names.add(f'spread_bb_bbl_{window}')
        # Bivariate
        for (bid_col, ask_col) in BID_ASK_PAIRS:
            if not is_etf:
                feature_names.add(f'{ask_col}_minus_{bid_col}')
                feature_names.add(f'{ask_col}_div_{bid_col}')
        for (mid_col, other_col) in MID_BID_ASK_PAIRS:
            if not is_etf:
                feature_names.add(f'{mid_col}_minus_{other_col}')
                feature_names.add(f'{mid_col}_div_{other_col}')
        for prefix in ['open', 'high', 'low', 'close', 'bid', 'ask', 'mid']:
            h = f'{prefix}_high'
            l = f'{prefix}_low'
            if not is_etf or prefix in ['open', 'high', 'low', 'close']:
                feature_names.add(f'{h}_minus_{l}')
                feature_names.add(f'{h}_div_{l}')
        if not is_etf:
            feature_names.add('bid_ask_bounce')
        return sorted(feature_names)

    forex_features = enumerate_features(is_etf=False)
    etf_features = enumerate_features(is_etf=True)
    print(f"Forex features: {len(forex_features)}")
    print(f"ETF features: {len(etf_features)}")
    # Optionally print feature names
    # for f in forex_features: print(f)
    # for f in etf_features: print(f) 