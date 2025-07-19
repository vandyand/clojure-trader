import os
import psycopg2
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from datetime import datetime
import argparse
import json

DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Connect to DB
def get_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def fetch_data(n_rows=10000):
    # Fetch a sample for feature selection
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT * FROM candles
            WHERE feature_1 IS NOT NULL
            ORDER BY random()
            LIMIT {n_rows}
        """, conn)
    return df

def get_feature_cols(df):
    # Define columns that are purely metadata or original complex types, not candidates for selection by default.
    # The 'features' column here would be the raw JSONB string if it was loaded directly, which it isn't
    # by the time this function is called usually; fetch_data_for_instrument expands it.
    metadata_cols = set([
        'timestamp', 'instrument', 'granularity', 'features' # 'features' is the JSONB column itself
    ])
    
    # Consider all other columns as potential features, including OHLCV and generated indicators.
    # The df passed here should already have features expanded from JSONB by fetch_data_for_instrument.
    candidate_cols = [col for col in df.columns if col not in metadata_cols]
    
    # Filter out columns that are all NaN or >99% zero or non-numeric if not handled before
    filtered_cols = []
    for col in candidate_cols:
        s = df[col]
        if s.isnull().all():
            continue
        if (s == 0).mean() > 0.99:
            continue
        filtered_cols.append(col)
    return filtered_cols

def get_target(df):
    # Example: next-period up/down as binary target
    # You may want to customize this for your use case
    return (df['close'].shift(-1) > df['close']).astype(int)[:-1]

def ensemble_feature_selection(df, y, feature_cols, n_select=50):
    X = df[feature_cols].iloc[:-1].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    # 1. Tree-based (RandomForest)
    rf = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)
    rf.fit(X_scaled, y)
    rf_importance = rf.feature_importances_
    # 2. L1-regularized Logistic Regression
    l1 = LogisticRegression(penalty='l1', solver='liblinear', max_iter=1000, random_state=42)
    l1.fit(X_scaled, y)
    l1_importance = np.abs(l1.coef_[0])
    # 3. XGBoost
    xgb_clf = xgb.XGBClassifier(n_estimators=100, n_jobs=-1, random_state=42, verbosity=0)
    xgb_clf.fit(X_scaled, y)
    xgb_importance = xgb_clf.feature_importances_
    # 4. Permutation importance (on RF)
    perm = permutation_importance(rf, X_scaled, y, n_repeats=3, random_state=42, n_jobs=-1)
    perm_importance = perm.importances_mean
    # Aggregate: average rank
    importances = np.vstack([rf_importance, l1_importance, xgb_importance, perm_importance])
    ranks = np.argsort(np.argsort(-importances, axis=1), axis=1)  # descending order
    avg_rank = ranks.mean(axis=0)
    # Decorrelate: remove highly correlated features
    selected_idx = np.argsort(avg_rank)[:n_select*2]  # take more for decorrelation
    selected_features = [feature_cols[i] for i in selected_idx]
    X_sel = df[selected_features].iloc[:-1].fillna(0)
    corr = X_sel.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
    decorrelated = [f for f in selected_features if f not in to_drop][:n_select]
    # Prepare output: (feature, avg_rank)
    feature_ranks = [(f, avg_rank[feature_cols.index(f)]) for f in decorrelated]
    return feature_ranks

def save_selected_features(feature_ranks, method='ensemble'):
    with get_conn() as conn:
        with conn.cursor() as cur:
            for rank, (feature, score) in enumerate(feature_ranks):
                cur.execute('''
                    INSERT INTO selected_features (feature_name, selection_method, rank, selected_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (feature_name) DO UPDATE SET selection_method=EXCLUDED.selection_method, rank=EXCLUDED.rank, selected_at=EXCLUDED.selected_at
                ''', (feature, method, rank+1, datetime.now()))
        conn.commit()

OANDA_INSTRUMENTS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]

FOREX_INSTRUMENTS = set(OANDA_INSTRUMENTS)

def fetch_data_for_instrument(instrument, n_rows=10000, use_etf_table=False):
    table = 'etf_features' if use_etf_table else 'forex_features'
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT * FROM {table}
            WHERE instrument = %s AND granularity = 'D' AND features IS NOT NULL
            ORDER BY random()
            LIMIT {n_rows}
        """, conn, params=(instrument,))
    # Expand features JSON into columns
    if 'features' not in df.columns:
        print(f"No features column found in {table} for {instrument}")
        return pd.DataFrame()  # Return empty dataframe - fail gracefully
        
    if df.empty:
        print(f"No data found in {table} for {instrument}")
        return df
        
    # Convert Series to DataFrame if needed
    features_df = None
    try:
        def expand_features(x):
            if isinstance(x, dict):
                return pd.Series(x)
            elif isinstance(x, str):
                return pd.Series(json.loads(x))
            else:
                return pd.Series()
        features_df = df['features'].apply(expand_features)
    except Exception as e:
        print(f"Error expanding features for {instrument}: {e}")
        return df
        
    df = pd.concat([df, features_df], axis=1)
    
    # Ensure raw columns are present at top level for both ETF and forex
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col not in df.columns:
            # Check if features_df is a Series or DataFrame
            if features_df is not None:
                if hasattr(features_df, 'columns'): 
                    # It's a DataFrame
                    if col in features_df.columns:
                        df[col] = features_df[col]
                else:
                    # It's a Series, check if the column exists as an index
                    if col in features_df.index:
                        df[col] = features_df[col]
                        
            # Look for columns directly that start with the prefix
            fallback_cols = [c for c in df.columns if c.startswith(f'{col}_')]
            if fallback_cols:
                df[col] = df[fallback_cols[0]]
                print(f"[WARN] Used fallback {fallback_cols[0]} for missing {col} in {instrument}")
            else:
                print(f"[WARN] {col} missing for instrument {instrument}")
    return df

def save_selected_features_per_instrument(instrument, feature_ranks, method='ensemble'):
    with get_conn() as conn:
        with conn.cursor() as cur:
            for rank, (feature, score) in enumerate(feature_ranks):
                cur.execute('''
                    INSERT INTO selected_features_per_instrument (instrument, feature_name, selection_method, rank, selected_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (instrument, feature_name) DO UPDATE SET selection_method=EXCLUDED.selection_method, rank=EXCLUDED.rank, selected_at=EXCLUDED.selected_at
                ''', (instrument, feature, method, rank+1, datetime.now()))
        conn.commit()

def already_pruned_instruments():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT instrument FROM selected_features_per_instrument GROUP BY instrument HAVING COUNT(*) >= 29;")
            return set(row[0] for row in cur.fetchall())

def get_etf_instruments():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT instrument FROM etf_features
                WHERE granularity = 'D'
                ORDER BY instrument;
            """)
            return [row[0] for row in cur.fetchall()]

def get_forex_instruments():
    return list(OANDA_INSTRUMENTS)

def main():
    parser = argparse.ArgumentParser(description="Per-instrument feature pruning.")
    parser.add_argument('--instrument', type=str, help='Instrument to prune features for (e.g. EUR_USD)')
    parser.add_argument('--n_features', type=int, help='Number of features to select per instrument')
    parser.add_argument('--etf', action='store_true', help='Prune ETF instruments instead of forex')
    args = parser.parse_args()
    if args.etf:
        instruments = get_etf_instruments()
        n_features = args.n_features if args.n_features else 23
    else:
        instruments = [args.instrument] if args.instrument else get_forex_instruments()
        n_features = args.n_features if args.n_features else 29
    pruned = already_pruned_instruments()
    for instrument in instruments:
        if instrument in pruned:
            print(f"Skipping {instrument}, already pruned.")
            continue
        print(f'Fetching data for {instrument}...')
        df = fetch_data_for_instrument(instrument, n_rows=20000, use_etf_table=args.etf)
        feature_cols = get_feature_cols(df)
        y = get_target(df)
        print(f'Feature selection on {len(feature_cols)} features, {len(df)} rows for {instrument}')
        feature_ranks = ensemble_feature_selection(df, y, feature_cols, n_select=n_features)
        print(f'Selected features for {instrument}:')
        for f, score in feature_ranks:
            print(f, score)
        save_selected_features_per_instrument(instrument, feature_ranks)
        print(f'Saved selected features for {instrument} to DB.')

if __name__ == '__main__':
    main() 