#!/usr/bin/env python
"""
Crypto Trading System - Main integration module that ties together the fusion autoencoder
and the RL policy network to create a complete trading system for cryptocurrencies.
"""
import os
import sys
import argparse
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import logging
from datetime import datetime, timedelta
import seaborn as sns
import json

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_rl.policy_network import CryptoRLTrader, FusionAutoencoder, RewardCalculator
from crypto_rl.data_fetcher import CryptoMarketDataFetcher
from crypto_rl.constants import CRYPTO_PAIRS_BY_LIQUIDITY, ETF_SYMBOLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"crypto_trading_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CryptoTradingSystem")

class CryptoTradingSystem:
    """
    High-level interface for the crypto trading system that combines the fusion autoencoder
    and RL policy network. Now supports both long and short positions for cryptocurrencies.
    """
    def __init__(self, 
                models_dir: str = None, 
                actor_lr: float = 1e-4,
                critic_lr: float = 1e-3,
                train_on_startup: bool = False):
        self.models_dir = models_dir or os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Initialize components
        self.trader = CryptoRLTrader(actor_lr=actor_lr, critic_lr=critic_lr)
        self.reward_calculator = RewardCalculator()
        self.data_fetcher = CryptoMarketDataFetcher()
        
        # Initialize trading state variables
        self.previous_positions = torch.zeros(len(CRYPTO_PAIRS_BY_LIQUIDITY))
        self.transaction_cost_rate = 0.001  # 0.1% per trade (higher for crypto)
        self.missing_instruments = []
        
        # Training state
        self.is_training = False
        self.current_epoch = 0
        self.total_epochs = 0
        
        # Initialize metrics
        self.metrics = {
            'epoch_rewards': [],
            'epoch_returns': [],
            'epoch_sharpe': [],
            'epoch_losses': [],
            'epoch_entropy': []
        }
        
        if train_on_startup:
            self.train()
    
    def train(self, epochs: int = 100, batch_size: int = 32):
        """
        Train the trading system.
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
        """
        self.is_training = True
        self.current_epoch = 0
        self.total_epochs = epochs
        
        # Load market data
        market_data = self._load_market_data()
        
        # Training loop
        for epoch in range(epochs):
            self.current_epoch = epoch
            epoch_metrics = self._train_epoch(market_data, batch_size)
            
            # Update metrics
            self.metrics['epoch_rewards'].append(epoch_metrics['reward'])
            self.metrics['epoch_returns'].append(epoch_metrics['return'])
            self.metrics['epoch_sharpe'].append(epoch_metrics['dsr'])
            self.metrics['epoch_losses'].append(epoch_metrics['loss'])
            # Optionally add entropy if available
            if 'entropy' in epoch_metrics:
                self.metrics['epoch_entropy'].append(epoch_metrics['entropy'])
            
            # Save checkpoint
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(epoch + 1)
            
            # Print progress
            print(f"\nEpoch {epoch + 1}/{epochs}")
            print(f"Average Reward: {epoch_metrics['reward']:.4f}")
            print(f"Average Loss: {epoch_metrics['loss']:.4f}")
            print(f"Portfolio Return: {epoch_metrics['return']:.4f}")
            print(f"DSR: {epoch_metrics['dsr']:.4f}")
        
        self.is_training = False
        self.save_checkpoint(epochs)
    
    def evaluate(self, test_data: Dict = None, n_episodes: int = 100, episode_length: int = 1000) -> Dict[str, float]:
        """
        Evaluate the trading system on test data.
        
        Args:
            test_data: Optional test data dictionary
            n_episodes: Number of evaluation episodes
            episode_length: Length of each episode
            
        Returns:
            Dictionary of evaluation metrics
        """
        if test_data is None:
            test_data = self._load_market_data()
        
        # Initialize evaluation metrics
        episode_returns = []
        episode_sharpes = []
        episode_drawdowns = []
        episode_win_rates = []
        episode_avg_trade_returns = []
        all_positions = []
        
        # Make sure we track missing instruments
        if 'missing_instruments' in test_data:
            self.missing_instruments = test_data['missing_instruments']
        
        max_start_idx = max(0, len(test_data['features']) - episode_length - 1)
        
        # Evaluation loop
        for episode in range(n_episodes):
            # Random starting point
            start_idx = np.random.randint(0, max_start_idx) if max_start_idx > 0 else 0
            end_idx = min(start_idx + episode_length, len(test_data['features']) - 1)
            
            # Reset reward calculator
            self.previous_positions = torch.zeros(len(CRYPTO_PAIRS_BY_LIQUIDITY))
            
            # Episode data
            episode_states = test_data['features'][start_idx:end_idx]
            episode_price_changes = test_data['price_changes'][start_idx:end_idx]
            
            # Episode metrics
            episode_returns_list = []
            positions = []
            
            # Run episode
            for i in range(len(episode_states)):
                # Get current state
                state = torch.tensor(episode_states[i], dtype=torch.float32)
        
                # Get action (use mean for evaluation)
                action, _ = self.trader.get_action(state, training=False)
        
                # Calculate reward
                price_change = torch.tensor(episode_price_changes[i], dtype=torch.float32)
                reward_info = self.reward_calculator.calculate_reward(
                    action.detach().numpy(),
                    episode_price_changes[i]
                )
                
                # Update positions for transaction cost calculation
                portfolio_return = reward_info['portfolio_return']
                
                # Store results
                episode_returns_list.append(portfolio_return)
                positions.append(action.detach().numpy())
            
            # Calculate episode metrics
            episode_return = np.sum(episode_returns_list)
            episode_returns.append(episode_return)
            
            # Calculate Sharpe ratio
            if len(episode_returns_list) > 1 and np.std(episode_returns_list) > 0:
                sharpe = np.mean(episode_returns_list) / np.std(episode_returns_list) * np.sqrt(252)
            else:
                sharpe = 0
            episode_sharpes.append(sharpe)
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown(np.array(episode_returns_list))
            episode_drawdowns.append(max_drawdown)
        
            # Calculate win rate
            win_rate = np.mean(np.array(episode_returns_list) > 0) if episode_returns_list else 0
            episode_win_rates.append(win_rate)
            
            # Calculate average trade return
            avg_trade_return = np.mean(episode_returns_list) if episode_returns_list else 0
            episode_avg_trade_returns.append(avg_trade_return)
            
            # Store positions
            all_positions.extend(positions)
            
            # Print progress
            print(f"\rEvaluating episode {episode+1}/{n_episodes}: Return={episode_return:.4f}, Sharpe={sharpe:.4f}, MaxDD={max_drawdown:.4f}, WinRate={win_rate:.4f}, AvgReturn={avg_trade_return:.4f}", end="")
        
        print("\n")
        
        # Calculate overall metrics
        return {
            'total_return': np.mean(episode_returns),
            'sharpe_ratio': np.mean(episode_sharpes),
            'max_drawdown': np.mean(episode_drawdowns),
            'win_rate': np.mean(episode_win_rates),
            'avg_trade_return': np.mean(episode_avg_trade_returns),
            'positions': np.array(all_positions)
        }
    
    def generate_trading_signals(self, 
                               features: np.ndarray,
                               price_changes: np.ndarray,
                               days: int = 30) -> Dict[str, np.ndarray]:
        """
        Generate trading signals for a given period.
        
        Args:
            features: Market features [n_days, n_features]
            price_changes: Price changes [n_days, n_instruments]
            days: Number of days to simulate
            
        Returns:
            Dictionary containing trading signals and performance metrics
        """
        # Initialize arrays
        returns = []
        positions = []
        rewards = []
        
        # Simulation loop
        for i in range(min(days, len(features))):
            # Get current state
            state = torch.tensor(features[i], dtype=torch.float32).unsqueeze(0)
            
            # Get action
            action, _ = self.trader.get_action(state, training=False)
            
            # Calculate reward
            reward_info = self.reward_calculator.calculate_reward(
                action[0].detach().numpy(),
                price_changes[i] if i < len(price_changes) else np.zeros(len(CRYPTO_PAIRS_BY_LIQUIDITY))
            )
            
            # Store results
            returns.append(reward_info['portfolio_return'])
            positions.append(action[0].detach().numpy())
            rewards.append(reward_info['clipped_reward'])
        
        # Calculate metrics
        total_return = np.sum(returns)
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'returns': np.array(returns),
            'positions': np.array(positions),
            'rewards': np.array(rewards)
        }
    
    def plot_training_progress(self):
        """Plot training progress metrics."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot rewards
        axes[0, 0].plot(self.metrics['epoch_rewards'])
        axes[0, 0].set_title('Training Rewards')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Average Reward')
        
        # Plot returns
        axes[0, 1].plot(self.metrics['epoch_returns'])
        axes[0, 1].set_title('Portfolio Returns')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Average Return')
        
        # Plot Sharpe ratios
        axes[1, 0].plot(self.metrics['epoch_sharpe'])
        axes[1, 0].set_title('Differential Sharpe Ratio')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('DSR')
        
        # Plot losses
        axes[1, 1].plot(self.metrics['epoch_losses'])
        axes[1, 1].set_title('Training Losses')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Loss')
        
        plt.tight_layout()
        plt.savefig('crypto_training_progress.png')
        plt.show()
    
    def plot_position_heatmap(self, positions: np.ndarray, title: str = 'Crypto Position Heatmap'):
        """Plot position heatmap for crypto pairs."""
        plt.figure(figsize=(15, 8))
        
        # Create heatmap
        sns.heatmap(positions.T, 
                   xticklabels=range(len(positions)),
                   yticklabels=CRYPTO_PAIRS_BY_LIQUIDITY,
                   cmap='RdYlGn',
                   center=0,
                   cbar_kws={'label': 'Position Size'})
        
        plt.title(title)
        plt.xlabel('Time Step')
        plt.ylabel('Crypto Pair')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('crypto_position_heatmap.png')
        plt.show()
    
    def save_checkpoint(self, epoch: int):
        """Save a checkpoint of the model."""
        checkpoint_path = os.path.join(self.models_dir, f'crypto_checkpoint_epoch_{epoch}.pt')
        self.trader.save_model(checkpoint_path)
    
    def load_checkpoint(self, epoch: int):
        """Load a checkpoint of the model."""
        checkpoint_path = os.path.join(self.models_dir, f'crypto_checkpoint_epoch_{epoch}.pt')
        self.trader.load_model(checkpoint_path)
    
    def _load_market_data(self):
        """Load market data from data fetcher."""
        logger.info("Loading market data...")
        
        try:
            # Get feature vector for all instruments
            feature_vector = self.data_fetcher.prepare_feature_vector()
            
            if feature_vector is None:
                raise ValueError("Failed to prepare feature vector")
            
            # For now, we'll create synthetic price changes for training
            # In a real system, you would calculate actual price changes from historical data
            n_days = 1000  # Number of days of historical data
            n_instruments = len(CRYPTO_PAIRS_BY_LIQUIDITY)
            
            # Create synthetic features and price changes for training
            features = np.random.randn(n_days, len(feature_vector)) * 0.1
            price_changes = np.random.randn(n_days, n_instruments) * 0.02  # 2% daily volatility
            
            # Clean features: replace NaNs and Infs with zeros
            features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
            price_changes = np.nan_to_num(price_changes, nan=0.0, posinf=0.0, neginf=0.0)
            
            logger.info(f"Loaded market data: {features.shape} features, {price_changes.shape} price changes")
            
            return {
                'features': features,
                'price_changes': price_changes,
                'missing_instruments': []
            }
            
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            raise
    
    def _train_epoch(self, market_data: Dict, batch_size: int) -> Dict[str, float]:
        """
        Train for one epoch.
        
        Args:
            market_data: Market data dictionary
            batch_size: Batch size for training
            
        Returns:
            Dictionary of epoch metrics
        """
        # Initialize epoch metrics
        epoch_rewards = []
        epoch_returns = []
        epoch_dsr = []
        epoch_losses = []
        
        # Training loop
        for i in range(0, len(market_data['features']) - 1, batch_size):
            # Get batch
            batch_end = min(i + batch_size, len(market_data['features']) - 1)
            states = torch.tensor(market_data['features'][i:batch_end], dtype=torch.float32)
            next_states = torch.tensor(market_data['features'][i+1:batch_end+1], dtype=torch.float32)
            price_changes = market_data['price_changes'][i:batch_end]

            # Debug: Check for NaNs/Infs in input features
            if torch.isnan(states).any() or torch.isinf(states).any():
                print(f"NaN or Inf detected in input features at batch {i}")
                print(f"NaN count: {torch.isnan(states).sum().item()}, Inf count: {torch.isinf(states).sum().item()}")
                print(f"Feature stats: min={states.min().item()}, max={states.max().item()}, mean={states.mean().item()}")

            # Encode states through autoencoder
            encoded_states = self.trader.encode_state(states)
            if torch.isnan(encoded_states).any() or torch.isinf(encoded_states).any():
                print(f"NaN or Inf detected in encoded states at batch {i}")
                print(f"NaN count: {torch.isnan(encoded_states).sum().item()}, Inf count: {torch.isinf(encoded_states).sum().item()}")
                print(f"Encoded stats: min={encoded_states.min().item()}, max={encoded_states.max().item()}, mean={encoded_states.mean().item()}")

            encoded_next_states = self.trader.encode_state(next_states)
        
            # Get actions
            actions, log_probs = self.trader.get_action(states)
            
            # Calculate rewards
            rewards = []
            returns = []
            dsr_values = []
            
            for j in range(len(actions)):
                reward_info = self.reward_calculator.calculate_reward(
                    actions[j].detach().numpy(),
                    price_changes[j]
                )
                rewards.append(reward_info['clipped_reward'])
                returns.append(reward_info['portfolio_return'])
                dsr_values.append(reward_info['differential_sharpe'])
            
            # Convert to tensors
            rewards = torch.tensor(rewards, dtype=torch.float32)
            dones = torch.zeros(len(rewards), dtype=torch.float32)
            
            # Update policy
            metrics = self.trader.update_policy(
                states=states,
                actions=actions,
                rewards=rewards,
                next_states=next_states,
                dones=dones
            )
            
            # Store metrics
            epoch_rewards.extend(rewards.tolist())
            epoch_returns.extend(returns)
            epoch_dsr.extend(dsr_values)
            epoch_losses.append(metrics['actor_loss'])
        
        return {
            'reward': np.mean(epoch_rewards),
            'return': np.mean(epoch_returns),
            'dsr': np.mean(epoch_dsr),
            'loss': np.mean(epoch_losses)
        }
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns."""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (running_max - cumulative) / running_max
        return np.max(drawdown)

    def calculate_reward(self, 
                        current_positions: torch.Tensor,
                        price_changes: torch.Tensor,
                        current_portfolio_value: float) -> torch.Tensor:
        """
        Calculate reward for current positions and price changes.
        
        Args:
            current_positions: Current position sizes [n_instruments]
            price_changes: Price changes [n_instruments]
            current_portfolio_value: Current portfolio value (unused)
            
        Returns:
            Reward
        """
        
        # Zero out positions for missing instruments
        if hasattr(self, 'missing_instruments') and self.missing_instruments:
            for instrument in self.missing_instruments:
                idx = CRYPTO_PAIRS_BY_LIQUIDITY.index(instrument)
                current_positions[idx] = 0
                price_changes[idx] = 0
        
        # Calculate position returns
        position_returns = current_positions * price_changes
        
        # Calculate portfolio return
        portfolio_return = position_returns.sum()
        
        # Add transaction cost penalty - IMPROVED IMPLEMENTATION
        position_changes = torch.abs(current_positions - self.previous_positions)
        
        # Apply transaction costs per position instead of on the sum
        # This ensures fair treatment of both long and short positions
        transaction_costs = self.transaction_cost_rate * position_changes
        total_transaction_cost = transaction_costs.sum()
        
        # Calculate reward
        reward = portfolio_return - total_transaction_cost
        
        # Clip reward to prevent extreme values
        reward = torch.clamp(reward, -1.0, 1.0)
        
        # Update previous positions
        self.previous_positions = current_positions.clone()
        
        return reward

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Crypto Trading System')
    parser.add_argument('--train', action='store_true', help='Train the policy network')
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--eval', action='store_true', help='Evaluate the policy network')
    parser.add_argument('--sim', action='store_true', help='Run a trading simulation')
    parser.add_argument('--sim-days', type=int, default=20, help='Number of days to simulate')
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    logger.info("Starting Crypto Trading System")
    logger.info(f"Arguments: {args}")
    
    # Create trading system
    logger.info("Creating CryptoTradingSystem instance...")
    system = CryptoTradingSystem(train_on_startup=False)
    logger.info("CryptoTradingSystem created successfully")
    
    # Train if requested
    if args.train:
        system.train(epochs=args.epochs)
    
    # Evaluate if requested
    if args.eval:
        eval_results = system.evaluate()
        print("\nEvaluation Results:")
        print(f"Total Return: {eval_results['total_return']:.4f}")
        print(f"Sharpe Ratio: {eval_results['sharpe_ratio']:.4f}")
        print(f"Maximum Drawdown: {eval_results['max_drawdown']:.4f}")
    
    # Run simulation if requested
    if args.sim:
        logger.info(f"Starting simulation for {args.sim_days} days...")
        # Load market data for simulation
        logger.info("Loading market data...")
        market_data = system._load_market_data()
        logger.info("Market data loaded successfully")
        sim_results = system.generate_trading_signals(
            features=market_data['features'],
            price_changes=market_data['price_changes'],
            days=args.sim_days
        )
        print("\nSimulation Results:")
        print(f"Total Return: {sim_results['total_return']:.4f}")
        print(f"Sharpe Ratio: {sim_results['sharpe_ratio']:.4f}")
        
        # Plot position heatmap
        system.plot_position_heatmap(sim_results['positions'], '30-Day Crypto Trading Simulation')
    
    # If no action specified, generate current signals
    if not (args.train or args.eval or args.sim):
        logger.info("No specific action requested, generating current signals...")
        logger.info("Loading market data...")
        market_data = system._load_market_data()
        logger.info("Market data loaded successfully")
        signals = system.generate_trading_signals(
            features=market_data['features'],
            price_changes=market_data['price_changes'],
            days=1
        )
        
        # Print current positions
        print("\nCurrent Crypto Positions:")
        for i, pair in enumerate(CRYPTO_PAIRS_BY_LIQUIDITY):
            print(f"{pair}: {signals['positions'][-1][i]:.4f}")
        
        # Print portfolio metrics
        print("\nPortfolio Metrics:")
        print(f"Total Return: {signals['total_return']:.4f}")
        print(f"Sharpe Ratio: {signals['sharpe_ratio']:.4f}")

if __name__ == "__main__":
    main() 