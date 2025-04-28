import os
import psycopg2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from rl.data.autoencoder import fetch_selected_features, fetch_data, Autoencoder

# --- Custom Reward Function (from reward-info.md, numpy version) ---
def trading_reward_pipeline(raw_outputs, price_changes, mu_prev, sigma_sq_prev, beta=0.95):
    long = np.maximum(raw_outputs, 0)
    short = np.maximum(-raw_outputs, 0)
    alpha = long + short
    alpha_0 = np.sum(alpha)
    positions = alpha / (alpha_0 + 1e-8)
    abs_pos = np.abs(positions)
    p = abs_pos / (np.sum(abs_pos) + 1e-8)
    entropy = -np.sum(p * np.log(p + 1e-8))
    norm_entropy = entropy / np.log(len(positions)) if len(positions) > 1 else 0.0
    scaling = 1.0 - norm_entropy
    final_positions = positions * scaling
    R_t = np.sum(final_positions * price_changes)
    delta = R_t - mu_prev
    mu_t = mu_prev + beta * delta
    sigma_sq_t = sigma_sq_prev + beta * (R_t**2 - sigma_sq_prev)
    numerator = beta * delta - 0.5 * (beta**2) * sigma_sq_prev
    denominator = (sigma_sq_prev + beta * delta**2)**1.5 + 1e-12
    dsr = numerator / denominator
    confidence = 1.0 - 1.0 / (alpha_0 + 1.0)
    reward = dsr * confidence
    return reward, mu_t, sigma_sq_t

# --- Data Pipeline: Fetch features and log returns for a single instrument ---
def fetch_features_and_log_returns_single(feature_names, n_rows=50000, instrument='EUR_USD', granularity='H1'):
    cols = ','.join(['timestamp', 'close'] + feature_names)
    with psycopg2.connect(dbname=os.getenv('DB_NAME', 'rl_forex'), user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', 'password'), host=os.getenv('DB_HOST', 'localhost'), port=os.getenv('DB_PORT', '5432')) as conn:
        df = pd.read_sql(f"""
            SELECT {cols} FROM candles
            WHERE instrument = '{instrument}' AND granularity = '{granularity}' AND {feature_names[0]} IS NOT NULL
            ORDER BY timestamp
            LIMIT {n_rows+1}
        """, conn)
    df = df.fillna(0)
    features = df[feature_names].values[:-1].astype(np.float32)  # all but last row
    close = df['close'].values.astype(np.float32)
    log_returns = np.log(close[1:] / (close[:-1] + 1e-8))  # shape: (N-1,)
    return features, log_returns

# --- Policy Network with tanh output for long/short ---
class PolicyNet(nn.Module):
    def __init__(self, input_dim=20, hidden_dim=128, output_dim=1, use_attention=True):
        super().__init__()
        self.use_attention = use_attention
        if use_attention:
            self.attn = nn.MultiheadAttention(embed_dim=input_dim, num_heads=1, batch_first=True)
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
            nn.Tanh()  # Output in [-1, 1] for long/short
        )
    def forward(self, x):
        if self.use_attention:
            x = x.unsqueeze(1)
            x, _ = self.attn(x, x, x)
            x = x.squeeze(1)
        return self.mlp(x)

# --- Utility to get bottleneck features from autoencoder ---
def get_bottleneck_features(X, autoencoder_path="autoencoder.pt", bottleneck_dim=20):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    n_features = X.shape[1]
    model = Autoencoder(n_features, bottleneck_dim)
    model.load_state_dict(torch.load(autoencoder_path, map_location=device))
    model.eval()
    with torch.no_grad():
        X_tensor = torch.tensor(X, dtype=torch.float32, device=device)
        z = model.encoder(model.input_layer(X_tensor))
    return z.cpu().numpy()

# --- PPO Training Loop Skeleton ---
def ppo_train(policy_net, get_bottleneck_features, fetch_features_and_log_returns_single, fetch_selected_features, autoencoder_path, n_epochs=10, batch_size=256, lr=3e-4, weight_decay=1e-4):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    feature_names = fetch_selected_features()
    X, log_returns = fetch_features_and_log_returns_single(feature_names, n_rows=2000, instrument='EUR_USD', granularity='H1')
    Z = get_bottleneck_features(X, autoencoder_path=autoencoder_path, bottleneck_dim=20)
    Z = torch.tensor(Z, dtype=torch.float32, device=device)
    log_returns = torch.tensor(log_returns, dtype=torch.float32, device=device)
    policy_net = policy_net.to(device)
    optimizer = optim.Adam(policy_net.parameters(), lr=lr, weight_decay=weight_decay)
    value_net = nn.Sequential(
        nn.Linear(20, 64), nn.ReLU(), nn.Linear(64, 1)
    ).to(device)
    value_optimizer = optim.Adam(value_net.parameters(), lr=lr, weight_decay=weight_decay)
    clip_epsilon = 0.2
    gamma = 0.99
    lam = 0.95
    for epoch in range(n_epochs):
        logits = policy_net(Z).squeeze(-1)  # shape (N,)
        actions = logits  # Already in [-1, 1]
        mu_prev, sigma_sq_prev = 0.0, 0.0001
        rewards = []
        for i in range(actions.shape[0]):
            raw_outputs = np.array([actions[i].detach().cpu().numpy()])  # shape (1,)
            reward, mu_prev, sigma_sq_prev = trading_reward_pipeline(raw_outputs, np.array([log_returns[i].cpu().numpy()]), mu_prev, sigma_sq_prev)
            rewards.append(reward)
        rewards = torch.tensor(rewards, dtype=torch.float32, device=device)
        values = value_net(Z).squeeze(-1)
        advantages = (rewards - values.detach()).detach()
        actions_detached = actions.detach()
        old_log_probs = -((actions_detached - logits.detach())**2)
        for _ in range(4):
            logits_new = policy_net(Z).squeeze(-1)
            log_probs = -((actions_detached - logits_new)**2)
            ratio = torch.exp(log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            value_pred = value_net(Z).squeeze(-1)
            value_loss = (rewards - value_pred).pow(2).mean()
            loss = policy_loss + 0.5 * value_loss
            optimizer.zero_grad()
            value_optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            value_optimizer.step()
        if (epoch+1) % 2 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{n_epochs} - Policy loss: {policy_loss.item():.4f} - Value loss: {value_loss.item():.4f}")
    print("PPO training complete.")

# --- Main: Validation Run ---
def main():
    feature_names = fetch_selected_features()
    X, log_returns = fetch_features_and_log_returns_single(feature_names, n_rows=2000, instrument='EUR_USD', granularity='H1')
    Z = get_bottleneck_features(X, autoencoder_path="autoencoder.pt", bottleneck_dim=20)
    print(f"Bottleneck features shape: {Z.shape}")
    policy_net = PolicyNet(input_dim=20, hidden_dim=128, output_dim=1, use_attention=True)
    ppo_train(policy_net, get_bottleneck_features, fetch_features_and_log_returns_single, fetch_selected_features, autoencoder_path="autoencoder.pt", n_epochs=10, batch_size=256, lr=3e-4, weight_decay=1e-4)

if __name__ == '__main__':
    main() 