import os
import sqlite3
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import gym
from gym import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Custom neural network architecture
class ForexPolicyNetwork(BaseFeaturesExtractor):
    def __init__(self, observation_space, features_dim):
        super(ForexPolicyNetwork, self).__init__(observation_space, features_dim)
        input_dim = observation_space.shape[0]
        self.net = nn.Sequential(
            nn.Linear(input_dim, 500),
            nn.ReLU(),
            nn.Linear(500, 240),
            nn.ReLU(),
            nn.Linear(240, 120),
            nn.ReLU()
        )
        
        # Initialize weights properly
        for layer in self.net:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.constant_(layer.bias, 0.01)
        
    def forward(self, observations):
        return self.net(observations)

# Custom reward calculation functions
def calculate_alpha(raw_outputs):
    long = np.maximum(raw_outputs, 0)
    short = np.maximum(-raw_outputs, 0)
    return long + short, np.sum(long + short)

def position_entropy(positions):
    abs_pos = np.abs(positions)
    total = np.sum(abs_pos) + 1e-8
    p = abs_pos / total
    entropy = -np.sum(p * np.log(p + 1e-8))
    return entropy, entropy / np.log(len(positions) + 1e-8)

def differential_sharpe_ratio(R_t, mu_prev, sigma_sq_prev, beta=0.95):
    delta = R_t - mu_prev
    mu_t = mu_prev + beta * delta
    sigma_sq_t = sigma_sq_prev + beta * (R_t**2 - sigma_sq_prev)
    
    numerator = beta * delta - 0.5 * (beta**2) * sigma_sq_prev
    denominator = (sigma_sq_prev + beta * delta**2 + 1e-8)**1.5
    dsr = numerator / (denominator + 1e-8)
    
    # Clip extreme values
    dsr = np.clip(dsr, -10, 10)
    
    return dsr, mu_t, sigma_sq_t

# Trading environment
class ForexTradingEnv(gym.Env):
    def __init__(self, db_path, instrument_list):
        super(ForexTradingEnv, self).__init__()
        self.db_path = db_path
        self.instrument_list = instrument_list
        self.num_instruments = len(instrument_list)
        self.feature_dim = 15 * self.num_instruments
        
        # Load data
        self.features, self.returns = self.load_data()
        self.n_steps = len(self.features)
        
        # Sanity check: Remove any NaN values
        self.features = np.nan_to_num(self.features, nan=0.0)
        self.returns = np.nan_to_num(self.returns, nan=0.0)
        
        # Normalize features
        self.feature_means = np.mean(self.features, axis=0)
        self.feature_stds = np.std(self.features, axis=0)
        
        # Avoid division by zero
        zero_std_indices = self.feature_stds < 1e-8
        self.feature_stds[zero_std_indices] = 1.0
        
        self.features = (self.features - self.feature_means) / self.feature_stds
        
        # Define action and observation spaces
        self.action_space = spaces.Box(low=-1, high=1, shape=(self.num_instruments,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.feature_dim,), dtype=np.float32)
        
        # Initialize state
        self.reset()
        
    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        
        # Load ONLY Fibonacci features (15 per instrument)
        print("🔍 Loading Fibonacci features...")
        fib_features = [f'feat_{p}' for p in [1,2,3,5,8,13,21,34,55,89,144,233,377,610,987]]
        features_query = f"SELECT time, instrument, {','.join(fib_features)} FROM aligned_features"
        features_df = pd.read_sql_query(features_query, conn)
        
        # Transform to time-indexed, instrument-sorted format
        instruments_sorted = sorted(features_df['instrument'].unique())
        features_df = features_df.sort_values(['time', 'instrument'])
        feature_values = features_df[fib_features].values
        
        # Reshape to (timesteps, instruments * features)
        features = feature_values.reshape(
            features_df['time'].nunique(),
            len(instruments_sorted) * len(fib_features)
        )
        
        # Load returns using aligned candles
        print("🔍 Loading returns with aligned data...")
        returns_query = """
        SELECT time, instrument, 
               (close / LAG(close) OVER (PARTITION BY instrument ORDER BY time) - 1) AS return
        FROM aligned_candles 
        WHERE close IS NOT NULL
        """
        returns_df = pd.read_sql_query(returns_query, conn)
        
        # Pivot with properly ordered instruments
        returns_pivot = returns_df.pivot(index='time', columns='instrument', values='return')
        returns = returns_pivot[instruments_sorted].values
        
        conn.close()
        print(f"✅ Data loaded: {features.shape[0]} timesteps, {returns.shape[0]} returns")
        return features, returns

    def reset(self):
        self.current_step = 0
        self.dsr_mu = 0.0
        self.dsr_sigma_sq = 0.0001
        return self.features[self.current_step]
    
    def step(self, action):
        # Calculate positions using Dirichlet-inspired method
        alpha, alpha_0 = calculate_alpha(action)
        positions = alpha / (alpha_0 + 1e-8)
        _, norm_entropy = position_entropy(positions)
        scaling_factor = 1.0 - norm_entropy
        final_positions = positions * scaling_factor
        
        # Get returns for this timestep
        returns = self.returns[self.current_step]
        portfolio_return = np.sum(final_positions * returns)
        
        # Calculate reward
        dsr, self.dsr_mu, self.dsr_sigma_sq = differential_sharpe_ratio(
            portfolio_return, self.dsr_mu, self.dsr_sigma_sq
        )
        confidence = 1.0 - 1.0 / (alpha_0 + 1.0)
        reward = dsr * confidence
        
        # Clip reward to prevent extreme values
        reward = np.clip(reward, -10, 10)
        
        # Prepare for next step
        self.current_step += 1
        done = self.current_step >= self.n_steps - 1
        next_obs = self.features[self.current_step] if not done else self.features[0]
        
        return next_obs, reward, done, {
            'portfolio_return': portfolio_return,
            'positions': final_positions,
            'dsr': dsr,
            'confidence': confidence
        }

# Main training function
def train_forex_model():
    # Configuration
    DB_PATH = 'data/forex_candles.sqlite3'
    
    # Use all instruments for full training
    INSTRUMENTS = ['EUR_USD', 'USD_JPY', 'GBP_USD', 'AUD_USD', 'USD_CAD', 
                   'NZD_USD', 'USD_CHF', 'EUR_GBP', 'EUR_JPY', 'GBP_JPY',
                   'AUD_JPY', 'EUR_AUD', 'EUR_CAD', 'EUR_CHF', 'EUR_NZD',
                   'GBP_AUD', 'GBP_CAD', 'GBP_CHF', 'CAD_JPY', 'CHF_JPY']
    total_timesteps = 1_000_000
    
    # Create environment
    env = ForexTradingEnv(DB_PATH, INSTRUMENTS)
    env = DummyVecEnv([lambda: env])
    
    # Policy configuration
    features_dim = 15 * len(INSTRUMENTS)  # 15 features per instrument
    policy_kwargs = {
        'features_extractor_class': ForexPolicyNetwork,
        'features_extractor_kwargs': {'features_dim': 120},  # Output dimension
        'net_arch': []  # Our custom network handles all layers
    }
    
    # Create PPO model with gradient clipping
    model = PPO(
        "MlpPolicy",
        env,
        policy_kwargs=policy_kwargs,
        verbose=1,
        tensorboard_log="./tensorboard/",
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        max_grad_norm=0.5  # Gradient clipping
    )
    
    # Set up checkpoint saving
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path="./checkpoints/",
        name_prefix="forex_ppo"
    )
    
    # Train the model
    print(f"Starting full training with {len(INSTRUMENTS)} instruments...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=checkpoint_callback,
        tb_log_name="forex_training"
    )
    
    # Save final model
    model.save("forex_ppo_final")
    print("Training completed and model saved!")

if __name__ == "__main__":
    train_forex_model()
