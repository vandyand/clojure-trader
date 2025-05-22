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

# Database connection settings
DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# List of forex instruments
OANDA_INSTRUMENTS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

class ScaledTanhInput(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))
    def forward(self, x):
        return torch.tanh(self.scale * x + self.bias)

class Autoencoder(nn.Module):
    def __init__(self, n_features, bottleneck_dim):
        super().__init__()
        self.input_layer = ScaledTanhInput(n_features)
        self.encoder = nn.Sequential(
            nn.Linear(n_features, 32),
            nn.ReLU(),
            nn.Linear(32, bottleneck_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, 32),
            nn.ReLU(),
            nn.Linear(32, n_features)
        )
    def forward(self, x):
        x = self.input_layer(x)
        z = self.encoder(x)
        return self.decoder(z)

# Fetch per-instrument selected features for forex
def fetch_selected_features_per_instrument(n_features):
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT instrument, feature_name FROM selected_features_per_instrument
            WHERE instrument IN {tuple(OANDA_INSTRUMENTS)}
              AND rank <= {n_features}
            ORDER BY instrument, rank
        """, conn)
    features = {inst: [] for inst in OANDA_INSTRUMENTS}
    for _, row in df.iterrows():
        features[row['instrument']].append(row['feature_name'])
    return features

# Fetch FX data matrix (concatenated features across instruments)
def fetch_fx_data(feature_dict, n_rows):
    # Build select clauses and join clauses for candles_wide
    select_clauses = []
    join_clauses = []
    base_inst = OANDA_INSTRUMENTS[0]
    for inst in OANDA_INSTRUMENTS:
        for feat in feature_dict[inst]:
            select_clauses.append(f"t_{inst}.features->>'{feat}' AS \"{inst}__{feat}\"")
    for inst in OANDA_INSTRUMENTS[1:]:
        join_clauses.append(
            f"JOIN candles_wide t_{inst} ON t_{inst}.timestamp = t_{base_inst}.timestamp"
            f" AND t_{inst}.instrument = '{inst}' AND t_{inst}.granularity = 'D'"
        )
    sql = f"""
        SELECT t_{base_inst}.timestamp,
               {', '.join(select_clauses)}
        FROM candles_wide t_{base_inst}
        {' '.join(join_clauses)}
        WHERE t_{base_inst}.instrument = '{base_inst}' AND t_{base_inst}.granularity = 'D'
        ORDER BY t_{base_inst}.timestamp DESC
        LIMIT {n_rows}
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    df = df.drop(columns=['timestamp'])
    return df.fillna(0).values.astype(np.float32), list(df.columns)

# Fetch ETF data matrix
def fetch_etf_data(n_rows):
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT features FROM etf_features
            WHERE features IS NOT NULL
            ORDER BY random()
            LIMIT {n_rows}
        """, conn)
    def expand_feat(x):
        if isinstance(x, dict):
            return pd.Series(x)
        return pd.Series(json.loads(x))
    features_df = df['features'].apply(expand_feat)
    features_df = features_df.fillna(0)
    return features_df.values.astype(np.float32), list(features_df.columns)

# Training routine (generic)
def train_autoencoder(X, n_epochs, batch_size, lr, bottleneck_dim, weight_decay):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = Autoencoder(X.shape[1], bottleneck_dim).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.MSELoss()
    dataset = TensorDataset(torch.tensor(X))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    print(f"Training consolidated autoencoder (input dim={X.shape[1]}, bottleneck={bottleneck_dim}) for {n_epochs} epochs...")
    for epoch in range(n_epochs):
        model.train()
        total_loss = 0.0
        for (batch,) in loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            recon = model(batch)
            loss = criterion(recon, batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch.size(0)
        avg_loss = total_loss / len(dataset)
        if epoch % 10 == 0 or epoch == n_epochs - 1:
            print(f"Epoch {epoch+1}/{n_epochs} - Loss: {avg_loss:.6f}")
    return model

# Utility for printing stats
def print_input_stats(X, names, title="Input data statistics"):
    print(f"{title}:")
    for i, name in enumerate(names):
        col = X[:, i]
        pct_zero = (col == 0).mean() * 100
        print(f"{name:30s} mean={col.mean():.4f} std={col.std():.4f} "
              f"min={col.min():.4f} max={col.max():.4f} %zero={pct_zero:.1f}")
    print("---")

# Recon examples
def print_recon_examples(model, X, n=3, title="Recon example"):
    device = next(model.parameters()).device
    model.eval()
    X_t = torch.tensor(X[:n], dtype=torch.float32).to(device)
    with torch.no_grad():
        recon = model(X_t).cpu().numpy()
    for i in range(n):
        print(f"{title} {i+1} input:   {np.round(X[i],4)}")
        print(f"{title} {i+1} recon:   {np.round(recon[i],4)}")
        print(f"Diff: {np.round(X[i]-recon[i],4)}\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train consolidated AE combining FX and ETF latents.")
    parser.add_argument('--fx_bottleneck', type=int, default=149, help='Bottleneck size of forex AE')
    parser.add_argument('--etf_bottleneck', type=int, default=8, help='Bottleneck size of ETF AE')
    parser.add_argument('--combined_bottleneck', type=int, default=32, help='Bottleneck size of consolidated AE')
    parser.add_argument('--n_features', type=int, default=29, help='Features per forex instrument')
    parser.add_argument('--n_rows', type=int, default=20000, help='Rows to sample for each section')
    parser.add_argument('--fx_model', type=str, default='autoencoder_fx.pt', help='Path to pretrained forex AE')
    parser.add_argument('--etf_model', type=str, default='autoencoder_etf.pt', help='Path to pretrained ETF AE')
    parser.add_argument('--epochs', type=int, default=200, help='Training epochs for consolidated AE')
    parser.add_argument('--batch', type=int, default=256, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-3, help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='L2 weight decay')
    args = parser.parse_args()

    # Fetch FX data
    print("Fetching selected features per instrument...")
    fx_feat_dict = fetch_selected_features_per_instrument(args.n_features)
    print("Fetching FX data...")
    X_fx, fx_names = fetch_fx_data(fx_feat_dict, args.n_rows)
    print(f"FX data shape: {X_fx.shape}")
    print_input_stats(X_fx, fx_names, title="Forex feature input stats")

    # Fetch ETF data
    print("Fetching ETF data...")
    X_etf, etf_names = fetch_etf_data(args.n_rows)
    print(f"ETF data shape: {X_etf.shape}")
    print_input_stats(X_etf, etf_names, title="ETF feature input stats")

    # Load pretrained AEs
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    fx_ae = Autoencoder(X_fx.shape[1], args.fx_bottleneck).to(device)
    fx_ae.load_state_dict(torch.load(args.fx_model, map_location=device))
    fx_ae.eval()
    etf_ae = Autoencoder(X_etf.shape[1], args.etf_bottleneck).to(device)
    etf_ae.load_state_dict(torch.load(args.etf_model, map_location=device))
    etf_ae.eval()

    # Extract latent representations
    with torch.no_grad():
        Z_fx = fx_ae.encoder(fx_ae.input_layer(torch.tensor(X_fx).to(device))).cpu().numpy()
        Z_etf = etf_ae.encoder(etf_ae.input_layer(torch.tensor(X_etf).to(device))).cpu().numpy()
    combined_input = np.concatenate([Z_fx, Z_etf], axis=1)
    combined_names = [f"fx_latent_{i}" for i in range(Z_fx.shape[1])] + [f"etf_latent_{i}" for i in range(Z_etf.shape[1])]
    print(f"Combined latent shape: {combined_input.shape}")
    print_input_stats(combined_input, combined_names, title="Combined latent input stats")

    # Train consolidated autoencoder
    combined_ae = train_autoencoder(
        combined_input,
        n_epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        bottleneck_dim=args.combined_bottleneck,
        weight_decay=args.weight_decay
    )
    print("Consolidated autoencoder training complete.")
    print_recon_examples(combined_ae, combined_input, n=3, title="Combined AE")

    # Save model and feature names
    torch.save(combined_ae.state_dict(), 'autoencoder_combined.pt')
    with open('autoencoder_combined_features.txt', 'w') as f:
        for name in combined_names:
            f.write(name + '\n')
    print("Model saved as autoencoder_combined.pt and feature names as autoencoder_combined_features.txt") 