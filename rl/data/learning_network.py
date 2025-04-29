import os
import psycopg2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from .autoencoder import fetch_selected_features, fetch_data, Autoencoder, train_autoencoder
import time

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
            nn.Linear(hidden_dim, output_dim * 2)  # Output mean and std
        )
        
    def forward(self, x):
        if self.use_attention:
            x = x.unsqueeze(1)
            x, _ = self.attn(x, x, x)
            x = x.squeeze(1)
        out = self.mlp(x)
        mean = out[:, 0]
        std = torch.exp(out[:, 1])  # Ensure std is positive
        return mean, std

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

# --- Single-Instrument DSR Reward Function ---
def single_instrument_sharpe_reward(r_t, mu_prev, sigma_prev, beta=0.95):
    mu_t = mu_prev + beta * (r_t - mu_prev)
    sigma_t = np.sqrt(sigma_prev**2 + beta * ((r_t - mu_prev)**2 - sigma_prev**2))
    dsr = (mu_t / (sigma_t + 1e-8)) - (mu_prev / (sigma_prev + 1e-8))
    return dsr, mu_t, sigma_t

# --- PPO Training Loop Skeleton ---
def ppo_train(policy_net, get_bottleneck_features, fetch_features_and_log_returns_single, fetch_selected_features, autoencoder_path, n_epochs=100, batch_size=256, lr=3e-4, weight_decay=1e-4):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    feature_names = fetch_selected_features()
    print(f"Selected features: {feature_names}")
    
    print("Fetching data...")
    X, log_returns = fetch_features_and_log_returns_single(feature_names, n_rows=2000, instrument='EUR_USD', granularity='H1')
    print(f"Data shape - Features: {X.shape}, Log returns: {log_returns.shape}")
    
    print("Getting bottleneck features...")
    Z = get_bottleneck_features(X, autoencoder_path=autoencoder_path, bottleneck_dim=20)
    Z = torch.tensor(Z, dtype=torch.float32, device=device)
    log_returns = torch.tensor(log_returns, dtype=torch.float32, device=device)
    
    # Initialize networks
    policy_net = policy_net.to(device)
    optimizer = optim.Adam(policy_net.parameters(), lr=lr, weight_decay=weight_decay)
    value_net = nn.Sequential(
        nn.Linear(20, 64), nn.ReLU(), nn.Linear(64, 1)
    ).to(device)
    value_optimizer = optim.Adam(value_net.parameters(), lr=lr, weight_decay=weight_decay)
    
    # Learning rate scheduler (less aggressive)
    policy_scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.8, patience=20, verbose=True)
    value_scheduler = optim.lr_scheduler.ReduceLROnPlateau(value_optimizer, mode='min', factor=0.5, patience=5, verbose=True)
    
    # Training parameters
    clip_epsilon = 0.2
    gamma = 0.99
    lam = 0.95
    max_grad_norm = 0.5
    reward_clip = 10.0  # Clip rewards to [-10, 10]
    
    # Reward normalization with running statistics
    reward_mean = 0.0
    reward_std = 1.0
    reward_momentum = 0.99  # Increased momentum for more stable statistics
    
    # Early stopping
    best_sharpe = float('-inf')
    patience = 10
    patience_counter = 0
    best_policy_state = None
    
    print("\nStarting training...")
    for epoch in range(n_epochs):
        epoch_start_time = time.time()
        
        # Get policy distribution
        mean, std = policy_net(Z)
        dist = torch.distributions.Normal(mean, std)
        actions = dist.sample()
        log_probs = dist.log_prob(actions)
        
        # Calculate rewards using DSR for single instrument
        mu_prev, sigma_prev = 0.0, 1e-4
        rewards = []
        for i in range(actions.shape[0]):
            # For single instrument, action is scalar, log_return is scalar
            r_t = float(actions[i].detach().cpu().numpy() * log_returns[i].cpu().numpy())
            dsr, mu_prev, sigma_prev = single_instrument_sharpe_reward(r_t, mu_prev, sigma_prev)
            rewards.append(dsr)
        
        rewards = torch.tensor(rewards, dtype=torch.float32, device=device)
        
        # Clip rewards
        rewards = torch.clamp(rewards, -reward_clip, reward_clip)
        
        # Update reward normalization
        reward_mean = reward_momentum * reward_mean + (1 - reward_momentum) * rewards.mean().item()
        reward_std = reward_momentum * reward_std + (1 - reward_momentum) * rewards.std().item()
        normalized_rewards = (rewards - reward_mean) / (reward_std + 1e-8)
        
        # Calculate advantages
        values = value_net(Z).squeeze(-1)
        advantages = (normalized_rewards - values.detach()).detach()
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Store old log probs
        old_log_probs = log_probs.detach()
        
        # PPO updates
        policy_losses = []
        value_losses = []
        for _ in range(4):
            # Get new policy distribution
            mean_new, std_new = policy_net(Z)
            dist_new = torch.distributions.Normal(mean_new, std_new)
            log_probs_new = dist_new.log_prob(actions)
            
            # Calculate ratio and surrogate losses
            ratio = torch.exp(log_probs_new - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            value_pred = value_net(Z).squeeze(-1)
            value_loss = (normalized_rewards - value_pred).pow(2).mean()
            
            # Total loss
            loss = policy_loss + 0.5 * value_loss
            
            # Update with gradient clipping
            optimizer.zero_grad()
            value_optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy_net.parameters(), max_grad_norm)
            torch.nn.utils.clip_grad_norm_(value_net.parameters(), max_grad_norm)
            optimizer.step()
            value_optimizer.step()
            
            policy_losses.append(policy_loss.item())
            value_losses.append(value_loss.item())
        
        # Update learning rates
        mean_policy_loss = np.mean(policy_losses)
        mean_value_loss = np.mean(value_losses)
        policy_scheduler.step(mean_policy_loss)
        value_scheduler.step(mean_value_loss)
        
        # Calculate performance metrics
        with torch.no_grad():
            # Sharpe ratio of normalized rewards
            sharpe = normalized_rewards.mean() / (normalized_rewards.std() + 1e-8)
            # Average position size
            avg_position = actions.abs().mean()
            # Policy entropy
            entropy = dist.entropy().mean()
            
            epoch_time = time.time() - epoch_start_time
            
            print(f"\nEpoch {epoch+1}/{n_epochs} (Time: {epoch_time:.2f}s)")
            print(f"Policy loss: {mean_policy_loss:.4f} ± {np.std(policy_losses):.4f}")
            print(f"Value loss: {mean_value_loss:.4f} ± {np.std(value_losses):.4f}")
            print(f"Sharpe ratio: {sharpe.item():.4f}")
            print(f"Avg position: {avg_position.item():.4f}")
            print(f"Policy entropy: {entropy.item():.4f}")
            print(f"Reward mean: {reward_mean:.4f}, std: {reward_std:.4f}")
            print(f"Learning rates - Policy: {optimizer.param_groups[0]['lr']:.6f}, Value: {value_optimizer.param_groups[0]['lr']:.6f}")
            print("---")
            
            # Early stopping check
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_policy_state = {
                    'policy_state': policy_net.state_dict(),
                    'value_state': value_net.state_dict(),
                    'epoch': epoch,
                    'sharpe': sharpe.item()
                }
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"\nEarly stopping triggered! Best Sharpe: {best_sharpe:.4f} at epoch {best_policy_state['epoch']+1}")
                # Restore best model
                policy_net.load_state_dict(best_policy_state['policy_state'])
                value_net.load_state_dict(best_policy_state['value_state'])
                break
    
    print("\nPPO training complete.")
    # Save the best model
    torch.save(best_policy_state, 'best_policy.pt')
    print("Best model saved as best_policy.pt")

# --- Main: Validation Run ---
def main():
    train_autoencoder_and_ppo()

def train_autoencoder_and_ppo(n_epochs_autoencoder=400, n_epochs_ppo=100, batch_size=256, lr=3e-4, weight_decay=1e-4):
    if not os.path.exists("autoencoder.pt"):
        print("=== Starting Autoencoder Training ===")
        feature_names = fetch_selected_features()
        print("Selected features:", feature_names)
        print("Fetching data...")
        X = fetch_data(feature_names, n_rows=50000)
        print(f"Training autoencoder on {X.shape[0]} samples, {X.shape[1]} features")
        model = train_autoencoder(X, n_epochs=n_epochs_autoencoder, batch_size=batch_size, lr=lr, bottleneck_dim=20, weight_decay=weight_decay)
        print("Autoencoder training complete.")
        torch.save(model.state_dict(), "autoencoder.pt")
        print("Model saved as autoencoder.pt")
    else:
        print("Using existing autoencoder.pt")
    
    print("\n=== Starting PPO Training ===")
    policy_net = PolicyNet(input_dim=20, hidden_dim=128, output_dim=1, use_attention=True)
    ppo_train(policy_net, get_bottleneck_features, fetch_features_and_log_returns_single, fetch_selected_features, 
              autoencoder_path="autoencoder.pt", n_epochs=n_epochs_ppo, batch_size=batch_size, lr=lr, weight_decay=weight_decay)

if __name__ == '__main__':
    main() 