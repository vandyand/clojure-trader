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
    return [col for col in df.columns if col.startswith('feature_')]

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
    perm = permutation_importance(rf, X_scaled, y, n_repeats=5, random_state=42, n_jobs=-1)
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

def main():
    print('Fetching data...')
    df = fetch_data(20000)
    feature_cols = get_feature_cols(df)
    y = get_target(df)
    print(f'Feature selection on {len(feature_cols)} features, {len(df)} rows')
    feature_ranks = ensemble_feature_selection(df, y, feature_cols, n_select=50)
    print('Selected features:')
    for f, score in feature_ranks:
        print(f, score)
    save_selected_features(feature_ranks)
    print('Saved selected features to DB.')

if __name__ == '__main__':
    main() 