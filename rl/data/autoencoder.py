import os
import psycopg2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

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

def main():
    print("Fetching selected features...")
    feature_names = fetch_selected_features()
    print("Selected features:", feature_names)
    print("Fetching data...")
    X = fetch_data(feature_names, n_rows=50000)
    print(f"Training autoencoder on {X.shape[0]} samples, {X.shape[1]} features")
    model = train_autoencoder(X, n_epochs=400, batch_size=256, lr=1e-3, bottleneck_dim=20, weight_decay=1e-4)
    print("Training complete.")
    torch.save(model.state_dict(), "autoencoder.pt")
    print("Model saved as autoencoder.pt")

if __name__ == '__main__':
    main() 