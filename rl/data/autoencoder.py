import os
import psycopg2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import argparse

DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Connect to DB
def get_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

def fetch_selected_features():
    with get_conn() as conn:
        df = pd.read_sql("""
            SELECT feature_name FROM selected_features ORDER BY rank
        """, conn)
    return [row['feature_name'] for _, row in df.iterrows()]

def fetch_data(feature_names, n_rows=50000):
    cols = ','.join(feature_names)
    with get_conn() as conn:
        df = pd.read_sql(f"""
            SELECT {cols} FROM candles
            WHERE {feature_names[0]} IS NOT NULL
            ORDER BY random()
            LIMIT {n_rows}
        """, conn)
    return df.fillna(0).values.astype(np.float32)

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
        # Make sure hidden dimension is larger than bottleneck
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

def train_autoencoder(X, n_epochs=400, batch_size=256, lr=1e-3, bottleneck_dim=20, weight_decay=1e-4):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    n_features = X.shape[1]
    model = Autoencoder(n_features, bottleneck_dim).to(device)
    dataset = TensorDataset(torch.tensor(X))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.MSELoss()
    print(f"Training autoencoder with bottleneck size {bottleneck_dim} for {n_epochs} epochs (L2 weight decay {weight_decay})...")
    for epoch in range(n_epochs):
        model.train()
        total_loss = 0
        for (batch,) in loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            recon = model(batch)
            loss = criterion(recon, batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch.size(0)
        avg_loss = total_loss / len(dataset)
        if (epoch+1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{n_epochs} - Loss: {avg_loss:.6f}")
    return model

OANDA_INSTRUMENTS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]

def fetch_selected_features_per_instrument(n_features=29):
    # Returns a dict: {instrument: [feature1, ..., featureN]}
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

def fetch_fx_data(feature_dict, n_rows=50000):
    """
    Fetch a random sample of forex feature vectors by joining on timestamp
    directly from the forex_features table across all instruments.
    Returns X matrix and flattened feature names.
    """
    base_inst = OANDA_INSTRUMENTS[0]
    # Collect full feature names and build SELECT clauses
    all_features = []
    select_clauses = []
    for inst in OANDA_INSTRUMENTS:
        feats = feature_dict[inst]
        all_features += [f"{inst}__{f}" for f in feats]
        for f in feats:
            select_clauses.append(
                f"t_{inst}.features->>'{f}' AS \"{inst}__{f}\""
            )
    select_sql = ",\n        ".join(select_clauses)
    # Build JOIN clauses against forex_features
    join_sql = "\n    ".join([
        f"JOIN forex_features t_{inst}"
        f" ON t_{inst}.timestamp = t_{base_inst}.timestamp"
        f" AND t_{inst}.instrument = '{inst}' AND t_{inst}.granularity = 'D'"
        for inst in OANDA_INSTRUMENTS[1:]
    ])
    # Compose random-sampling SQL
    sql = f"""
        SELECT t_{base_inst}.timestamp,
        {select_sql}
        FROM forex_features t_{base_inst}
        {join_sql}
        WHERE t_{base_inst}.instrument = '{base_inst}' AND t_{base_inst}.granularity = 'D'
        ORDER BY random()
        LIMIT {n_rows}
    """
    with get_conn() as conn:
        df = pd.read_sql(sql, conn)
    df = df.drop(columns=['timestamp'])
    return df.fillna(0).values.astype(np.float32), all_features

def print_input_stats(X, feature_order):
    print("Input data statistics:")
    for i, feat in enumerate(feature_order):
        col = X[:, i]
        pct_zero = (col == 0).mean() * 100
        print(f"{feat:30s} mean={col.mean():.4f} std={col.std():.4f} min={col.min():.4f} max={col.max():.4f} %zero={pct_zero:.1f}")
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
    parser = argparse.ArgumentParser(description="Train AE-FX on all forex instruments.")
    parser.add_argument('--bottleneck', type=int, default=149, help='Bottleneck size (default: 149)')
    parser.add_argument('--n_features', type=int, default=29, help='Features per instrument (default: 29)')
    parser.add_argument('--n_rows', type=int, default=50000, help='Rows to sample (default: 50000)')
    parser.add_argument('--epochs', type=int, default=400, help='Training epochs (default: 400)')
    args = parser.parse_args()
    print("Fetching selected features per instrument...")
    feature_dict = fetch_selected_features_per_instrument(args.n_features)
    print("Fetching FX data...")
    X, feature_order = fetch_fx_data(feature_dict, n_rows=args.n_rows)
    print(f"Training autoencoder on {X.shape[0]} samples, {X.shape[1]} features (20x{args.n_features})")
    print_input_stats(X, feature_order)
    model = train_autoencoder(X, n_epochs=args.epochs, batch_size=256, lr=1e-3, bottleneck_dim=args.bottleneck, weight_decay=1e-4)
    print("Training complete.")
    print_recon_examples(model, X, n=3)
    torch.save(model.state_dict(), "autoencoder_fx.pt")
    with open("autoencoder_fx_features.txt", "w") as f:
        for feat in feature_order:
            f.write(feat + "\n")
    print("Model saved as autoencoder_fx.pt, feature order as autoencoder_fx_features.txt")

if __name__ == '__main__':
    main() 