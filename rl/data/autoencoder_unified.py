#!/usr/bin/env python
import os
import psycopg2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import argparse
import json
import time  # for logging durations

"""
List of FX instruments to include; only these will be fetched from selected_features_per_instrument.
"""
OANDA_INSTRUMENTS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]

# Database connection settings
db_params = dict(
    dbname=os.getenv('DB_NAME', 'rl_forex'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'password'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)

def get_conn():
    return psycopg2.connect(**db_params)

# Fetch per-instrument FX selected features
def fetch_selected_fx_features(n_features=29):
    # Only include selected FX instruments
    inst_tuple = tuple(OANDA_INSTRUMENTS)
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT instrument, feature_name
            FROM selected_features_per_instrument
            WHERE instrument IN {inst_tuple}
            ORDER BY instrument, rank
        """, conn)
    # Initialize feature list for each FX instrument
    features = {inst: [] for inst in OANDA_INSTRUMENTS}
    for _, row in df.iterrows():
        features[row['instrument']].append(row['feature_name'])
    return features

# Sample FX data by joining on timestamp across all instruments
def fetch_fx_data(feature_dict, n_rows=50000):
    instruments = list(feature_dict.keys())
    base = instruments[0]
    select_clauses = []
    all_feats = []
    for inst in instruments:
        feats = feature_dict[inst]
        all_feats += [f"{inst}__{f}" for f in feats]
        for f in feats:
            select_clauses.append(
                f"t_{inst}.features->>'{f}' AS \"{inst}__{f}\""
            )
    select_sql = ",\n        ".join(select_clauses)
    join_sql = "\n    ".join([
        f"JOIN forex_features t_{inst} ON t_{inst}.timestamp = t_{base}.timestamp"
        f" AND t_{inst}.instrument = '{inst}' AND t_{inst}.granularity = 'D'"
        for inst in instruments[1:]
    ])
    sql = f"""
        SELECT t_{base}.timestamp,
        {select_sql}
        FROM forex_features t_{base}
        {join_sql}
        WHERE t_{base}.instrument = '{base}' AND t_{base}.granularity = 'D'
        ORDER BY random()
        LIMIT {n_rows}
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    df = df.drop(columns=['timestamp']).fillna(0)
    print(f"[Fetch FX] Retrieved {df.shape[0]} samples x {df.shape[1]} FX features", flush=True)
    return df.values.astype(np.float32), df.columns.tolist()

# Sample ETF data from JSON features column
def fetch_etf_data(n_rows=50000):
    with get_conn() as conn:
        df = pd.read_sql(f"SELECT features FROM etf_features WHERE features IS NOT NULL ORDER BY random() LIMIT {n_rows}", conn)
    def expand(x):
        if isinstance(x, dict): return pd.Series(x)
        else: return pd.Series(json.loads(x))
    feats_df = df['features'].apply(expand).fillna(0)
    print(f"[Fetch ETF] Retrieved {feats_df.shape[0]} samples x {feats_df.shape[1]} ETF features", flush=True)
    return feats_df.values.astype(np.float32), feats_df.columns.tolist()

# Scaled tanh input layer
def scaled_tanh_input(n_features):
    return nn.Sequential(nn.Parameter(torch.ones(n_features)), nn.Parameter(torch.zeros(n_features)))

class ScaledTanhInput(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))
    def forward(self, x):
        return torch.tanh(self.scale * x + self.bias)

class Autoencoder(nn.Module):
    def __init__(self, n_features, bottleneck_dim=149):
        super().__init__()
        hidden = bottleneck_dim * 2
        self.input_layer = ScaledTanhInput(n_features)
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.ReLU(),
            nn.Linear(hidden, bottleneck_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, n_features)
        )
    def forward(self, x):
        x = self.input_layer(x)
        z = self.encoder(x)
        return self.decoder(z)

# Training loop
def train_autoencoder(X, bottleneck, epochs, batch_size=256, lr=1e-3, weight_decay=1e-4):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = Autoencoder(X.shape[1], bottleneck).to(device)
    print(f"[Train] Starting training: {X.shape[0]} samples x {X.shape[1]} features, bottleneck={bottleneck}, epochs={epochs}", flush=True)
    start_time = time.time()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.MSELoss()
    ds = TensorDataset(torch.tensor(X))
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)
    for ep in range(epochs):
        ep_start = time.time()
        model.train()
        tot = 0
        for (b,) in loader:
            b = b.to(device)
            optimizer.zero_grad()
            recon = model(b)
            loss = criterion(recon, b)
            loss.backward()
            optimizer.step()
            tot += loss.item() * b.size(0)
        # Log progress every 10 epochs and at first/last epoch
        if (ep+1) % 10 == 0 or ep == 0 or ep == epochs-1:
            avg_loss = tot / len(ds)
            ep_duration = time.time() - ep_start
            print(f"[Train] Epoch {ep+1}/{epochs} - Loss: {avg_loss:.6f} - {ep_duration:.2f}s/epoch", flush=True)
    total_time = time.time() - start_time
    print(f"[Train] Training completed in {total_time:.2f}s", flush=True)
    return model

# Print some examples
import numpy as _np

def print_recon_examples(model, X, n=3):
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        data = torch.tensor(X[:n], dtype=torch.float32).to(device)
        recon = model(data).cpu().numpy()
    for i in range(n):
        print(f"Example {i+1} diff norm: {_np.linalg.norm(X[i]-recon[i]):.4f}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bottleneck', type=int, default=149)
    p.add_argument('--n_fx_features', type=int, default=29)
    p.add_argument('--n_rows', type=int, default=50000)
    p.add_argument('--epochs', type=int, default=400)
    args = p.parse_args()

    print("Loading FX features…")
    fx_dict = fetch_selected_fx_features(args.n_fx_features)
    print("Sampling FX data…")
    X_fx, fx_order = fetch_fx_data(fx_dict, args.n_rows)
    print("Sampling ETF data…")
    X_etf, etf_order = fetch_etf_data(args.n_rows)

    X = np.hstack([X_fx, X_etf])
    order = fx_order + etf_order
    print(f"Combined data: {X.shape[0]} samples, {X.shape[1]} features")

    model = train_autoencoder(X, args.bottleneck, args.epochs)
    print("Training complete.")
    print_recon_examples(model, X)

    torch.save(model.state_dict(), "autoencoder_unified.pt")
    with open("autoencoder_unified_features.txt", "w") as f:
        for feat in order:
            f.write(feat + "\n")
    print("Saved unified autoencoder and feature list.")

if __name__ == '__main__':
    main() 