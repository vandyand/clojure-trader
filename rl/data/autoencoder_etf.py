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

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def fetch_etf_data(n_rows=50000):
    """
    Fetch random rows of ETF features (JSON) and expand into numeric matrix.
    Returns:
      X: numpy array of shape (n_rows, n_features)
      feature_order: list of feature names
    """
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT features FROM etf_features
            WHERE features IS NOT NULL
            ORDER BY random()
            LIMIT {n_rows}
        """, conn)

    # Expand JSON string or dict into DataFrame
    def expand_feat(x):
        if isinstance(x, dict):
            return pd.Series(x)
        else:
            return pd.Series(json.loads(x))

    features_df = df['features'].apply(expand_feat)
    features_df = features_df.fillna(0)

    X = features_df.values.astype(np.float32)
    feature_order = list(features_df.columns)
    return X, feature_order

class ScaledTanhInput(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))

    def forward(self, x):
        return torch.tanh(self.scale * x + self.bias)

class Autoencoder(nn.Module):
    def __init__(self, n_features, bottleneck_dim=8):
        super().__init__()
        self.input_layer = ScaledTanhInput(n_features)
        # Ensure hidden dimension larger than bottleneck
        hidden_dim = bottleneck_dim * 2
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, bottleneck_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_features)
        )

    def forward(self, x):
        x = self.input_layer(x)
        z = self.encoder(x)
        out = self.decoder(z)
        return out


def train_autoencoder(
    X,
    n_epochs=200,
    batch_size=256,
    lr=1e-3,
    bottleneck_dim=8,
    weight_decay=1e-4
):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    n_features = X.shape[1]
    model = Autoencoder(n_features, bottleneck_dim).to(device)
    optimizer = optim.Adam(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay
    )
    criterion = nn.MSELoss()
    dataset = TensorDataset(torch.tensor(X))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print(f"Training ETF autoencoder with bottleneck size {bottleneck_dim} for {n_epochs} epochs...")
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


def print_input_stats(X, feature_order):
    print("ETF Input data statistics:")
    for i, feat in enumerate(feature_order):
        col = X[:, i]
        pct_zero = (col == 0).mean() * 100
        print(f"{feat:30s} mean={col.mean():.4f} std={col.std():.4f} "
              f"min={col.min():.4f} max={col.max():.4f} %zero={pct_zero:.1f}")
    print("---")


def print_recon_examples(model, X, n=3):
    device = next(model.parameters()).device
    model.eval()
    X_tensor = torch.tensor(X[:n], dtype=torch.float32).to(device)
    with torch.no_grad():
        recon = model(X_tensor).cpu().numpy()
    for i in range(n):
        print(f"Example {i+1} input:   {np.round(X[i], 4)}")
        print(f"Example {i+1} recon:   {np.round(recon[i], 4)}")
        print(f"Diff: {np.round(X[i] - recon[i], 4)}\n")


def main():
    parser = argparse.ArgumentParser(description="Train AE-ETF on ETF features.")
    parser.add_argument('--bottleneck', type=int, default=149, help='Bottleneck size (default: 149)')
    parser.add_argument('--n_rows', type=int, default=50000, help='Rows to sample')
    parser.add_argument('--epochs', type=int, default=200, help='Training epochs')
    parser.add_argument('--batch', type=int, default=256, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-3, help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='L2 weight decay')
    args = parser.parse_args()

    # Load data
    print("Fetching ETF data...")
    X, feature_order = fetch_etf_data(args.n_rows)
    print(f"Data shape: {X.shape}")
    print_input_stats(X, feature_order)

    # Train
    model = train_autoencoder(
        X,
        n_epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        bottleneck_dim=args.bottleneck,
        weight_decay=args.weight_decay
    )

    # Evaluate & Save
    print("Training complete.")
    print_recon_examples(model, X, n=3)
    torch.save(model.state_dict(), "autoencoder_etf.pt")
    with open("autoencoder_etf_features.txt", "w") as f:
        for feat in feature_order:
            f.write(feat + "\n")
    print("Model saved as autoencoder_etf.pt and feature list as autoencoder_etf_features.txt")

if __name__ == '__main__':
    main() 