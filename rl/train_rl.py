import torch
import numpy as np
import pandas as pd
import os
import time
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple
from tqdm import tqdm

from rl.policy_network import RLTrader, FusionAutoencoder
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA

def load_market_data(n_features=1084, start_date=None, end_date=None, sample_size=None):
    """
    Load and prepare market data for training.
    This is a placeholder - in a real system, you would load your market data here.
    
    Args:
        n_features: Number of features (should match the fusion autoencoder input size)
        start_date: Start date for data range
        end_date: End date for data range
        sample_size: Number of samples to generate
        
    Returns:
        features: Dictionary of features for each instrument
        returns: Dictionary of returns for each instrument
    """
    # For now, generate synthetic market data
    n_days = 1000 if sample_size is None else sample_size
    
    # Generate synthetic features and returns
    features = {}
    returns = {}
    
    for instrument in PAIRS_BY_LIQUIDITY_OANDA:
        # Generate random walk for prices
        prices = np.cumprod(1 + np.random.randn(n_days) * 0.005)
        
        # Calculate daily returns
        daily_returns = np.diff(prices) / prices[:-1]
        
        # Generate synthetic features 
        daily_features = np.random.randn(n_days-1, n_features) * 0.1
        
        # Add some correlation between features and returns
        correlation_features = np.random.randint(0, n_features, 20)
        for i in correlation_features:
            daily_features[:, i] = daily_returns * (np.random.rand() * 5) + np.random.randn(n_days-1) * 0.1
        
        features[instrument] = daily_features
        returns[instrument] = daily_returns
    
    return features, returns

def train_policy(trader, batch_size=64, n_epochs=50, save_interval=5):
    """
    Train the RL policy network using market data.
    
    Args:
        trader: RLTrader instance
        batch_size: Batch size for training
        n_epochs: Number of training epochs
        save_interval: Save model every N epochs
    """
    # Define model save path
    save_path = 'models/rl_trader.pt'
    
    print("Loading market data...")
    # Handle case where autoencoder might not be loaded
    n_features = 1084  # Default number of features
    if trader.autoencoder is not None and hasattr(trader.autoencoder, 'n_features'):
        n_features = trader.autoencoder.n_features
        print(f"Using autoencoder with {n_features} input features")
    else:
        print(f"Autoencoder not available, using default {n_features} features")
    
    features, returns = load_market_data(n_features=n_features)
    
    # Get market data info
    instruments = list(features.keys())
    n_days = features[instruments[0]].shape[0]
    
    print(f"Training on {n_days} days of data for {len(instruments)} instruments")
    
    # Training metrics
    all_rewards = []
    all_losses = []
    all_portfolio_returns = []
    all_differential_sharpes = []
    
    for epoch in range(n_epochs):
        print(f"\nEpoch {epoch+1}/{n_epochs}")
        
        # Shuffle day order while maintaining alignment between features and returns
        day_indices = np.random.permutation(n_days-1)  # -1 because returns have one fewer day
        
        epoch_rewards = []
        epoch_losses = []
        epoch_portfolio_returns = []
        epoch_dsrs = []
        
        # Process data in batch_size chunks
        for batch_start in tqdm(range(0, len(day_indices) - batch_size, batch_size)):
            batch_indices = day_indices[batch_start:batch_start + batch_size]
            
            # Collect batch data
            states = []
            next_states = []
            raw_actions = []
            rewards = []
            dones = []
            
            # Process each day in the batch
            for day_idx in batch_indices:
                # Use the next day for the next state and returns
                next_day_idx = min(day_idx + 1, n_days-2)  # Ensure we don't go out of bounds
                
                # Prepare features and tensors
                current_features = features[instruments[0]][day_idx]
                current_features_tensor = torch.tensor(current_features, dtype=torch.float32).unsqueeze(0).to(trader.device)
                
                next_features = features[instruments[0]][next_day_idx]
                next_features_tensor = torch.tensor(next_features, dtype=torch.float32).unsqueeze(0).to(trader.device)
                
                # Get price changes for each instrument
                price_changes = np.array([returns[instr][next_day_idx] for instr in instruments])
                
                # Get action (pass raw features, not encoded)
                action, log_prob = trader.get_action(current_features_tensor)
                
                # Calculate reward
                reward_info = trader.reward_calculator.calculate_reward(
                    action[0].detach().cpu().numpy(),
                    price_changes
                )
                
                # Store for batch update (raw features, not encoded)
                states.append(current_features_tensor)
                next_states.append(next_features_tensor)
                raw_actions.append(log_prob.unsqueeze(0))
                rewards.append(reward_info['clipped_reward'])
                dones.append(False)
                
                # Track metrics
                epoch_rewards.append(reward_info['clipped_reward'])
                epoch_portfolio_returns.append(reward_info['portfolio_return'])
                epoch_dsrs.append(reward_info['differential_sharpe'])
            
            # Update policy with collected batch data if we have enough samples
            if len(states) >= batch_size:  
                # Convert lists to tensors for the update_policy method
                states_tensor = torch.cat(states, dim=0)
                next_states_tensor = torch.cat(next_states, dim=0)
                raw_actions_tensor = torch.cat(raw_actions, dim=0)
                rewards_tensor = torch.tensor(rewards, dtype=torch.float32).to(trader.device)
                dones_tensor = torch.tensor(dones, dtype=torch.float32).to(trader.device)
                
                update_info = trader.update_policy(states_tensor, raw_actions_tensor, rewards_tensor, next_states_tensor, dones_tensor)
                epoch_losses.append(update_info['actor_loss'])
        
        # Epoch summary
        avg_reward = np.mean(epoch_rewards) if epoch_rewards else 0
        avg_loss = np.mean(epoch_losses) if epoch_losses else 0
        avg_return = np.mean(epoch_portfolio_returns) if epoch_portfolio_returns else 0
        avg_dsr = np.mean(epoch_dsrs) if epoch_dsrs else 0
        
        print(f"Average Reward: {avg_reward:.4f}")
        print(f"Average Loss: {avg_loss:.4f}")
        print(f"Average Portfolio Return: {avg_return:.6f}")
        print(f"Average DSR: {avg_dsr:.4f}")
        
        # Track all metrics
        all_rewards.append(avg_reward)
        all_losses.append(avg_loss)
        all_portfolio_returns.append(avg_return)
        all_differential_sharpes.append(avg_dsr)
        
        # Save model periodically
        if (epoch + 1) % save_interval == 0:
            trader.save_model(save_path)
            
    # Final save
    trader.save_model(save_path)
    
    # Plot training progress
    plt.figure(figsize=(12, 10))
    
    plt.subplot(2, 2, 1)
    plt.plot(all_rewards)
    plt.title('Average Reward')
    plt.xlabel('Epoch')
    
    plt.subplot(2, 2, 2)
    plt.plot(all_losses)
    plt.title('Average Loss')
    plt.xlabel('Epoch')
    
    plt.subplot(2, 2, 3)
    plt.plot(all_portfolio_returns)
    plt.title('Average Portfolio Return')
    plt.xlabel('Epoch')
    
    plt.subplot(2, 2, 4)
    plt.plot(all_differential_sharpes)
    plt.title('Average Differential Sharpe')
    plt.xlabel('Epoch')
    
    plt.tight_layout()
    plt.savefig('training_progress.png')
    
    print(f"Training completed. Model saved.")
    return trader

def evaluate_policy(trader, n_days=100):
    """
    Evaluate the trained policy on test data.
    
    Args:
        trader: RLTrader instance
        n_days: Number of days to evaluate on
        
    Returns:
        Dictionary of evaluation metrics
    """
    print("Evaluating policy...")
    
    # Handle case where autoencoder might not be loaded
    n_features = 1084  # Default number of features
    if trader.autoencoder is not None and hasattr(trader.autoencoder, 'n_features'):
        n_features = trader.autoencoder.n_features
    
    features, returns = load_market_data(n_features=n_features, sample_size=n_days)
    
    # Evaluation metrics
    total_return = 0.0
    daily_returns = []
    positions_history = []
    
    # Get list of instruments
    instruments = list(features.keys())
    
    # Evaluate on each day
    for day in range(n_days - 1):  # -1 because we need next day returns
        # Get features for the current day
        current_features = features[instruments[0]][day]
        current_features_tensor = torch.tensor(current_features, dtype=torch.float32).unsqueeze(0).to(trader.device)
        
        # Get action (no random exploration during evaluation)
        with torch.no_grad():
            action, _ = trader.get_action(current_features_tensor, training=False)
        
        # Get positions
        positions = action[0].cpu().numpy()
        positions_history.append(positions)
        
        # Get price changes for each instrument
        price_changes = np.array([returns[instr][day] for instr in instruments])
        
        # Calculate portfolio return
        day_return = trader.reward_calculator.portfolio_return(positions, price_changes)
        daily_returns.append(day_return)
        total_return += day_return
    
    # Calculate metrics
    daily_returns = np.array(daily_returns)
    sharpe_ratio = np.mean(daily_returns) / (np.std(daily_returns) + 1e-6) * np.sqrt(252)  # Annualized
    max_drawdown = calculate_max_drawdown(daily_returns)
    
    # Plot equity curve
    equity_curve = np.cumprod(1 + daily_returns)
    plt.figure(figsize=(10, 6))
    plt.plot(equity_curve)
    plt.title('Equity Curve')
    plt.xlabel('Day')
    plt.ylabel('Equity')
    plt.savefig('equity_curve.png')
    
    results = {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'daily_returns': daily_returns,
        'positions_history': positions_history
    }
    
    print(f"Evaluation Results:")
    print(f"Total Return: {total_return:.4f}")
    print(f"Sharpe Ratio: {sharpe_ratio:.4f}")
    print(f"Max Drawdown: {max_drawdown:.4f}")
    
    return results

def calculate_max_drawdown(returns):
    """Calculate maximum drawdown from a series of returns."""
    cum_returns = np.cumprod(1 + np.array(returns))
    running_max = np.maximum.accumulate(cum_returns)
    drawdown = (cum_returns - running_max) / running_max
    return np.min(drawdown)

if __name__ == "__main__":
    # Create and train the RL trader
    trader = RLTrader(learning_rate=1e-4, gamma=0.99, entropy_weight=0.01)
    
    # Train the policy
    trader = train_policy(trader, batch_size=64, n_epochs=50, save_interval=5)
    
    # Evaluate the policy
    eval_results = evaluate_policy(trader, n_days=100)
    
    print("\nTraining and evaluation complete!") 