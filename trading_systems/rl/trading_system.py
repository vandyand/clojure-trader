#!/usr/bin/env python
"""
Trading System - Main integration module that ties together the fusion autoencoder
and the RL policy network to create a complete trading system.
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

from rl.policy_network import RLTrader, FusionAutoencoder, RewardCalculator
from rl.train_rl import train_policy, evaluate_policy, load_market_data
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA, ETF_SYMBOLS
from rl.data.autoencoder_fusion import load_instrument_data, get_selected_features_per_instrument

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"trading_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradingSystem")

class TradingSystem:
    """
    High-level interface for the trading system that combines the fusion autoencoder
    and RL policy network. Now supports both long and short positions.
    """
    def __init__(self, 
                models_dir: str = None, 
                actor_lr: float = 1e-4,
                critic_lr: float = 1e-3,
                train_on_startup: bool = False):
        self.models_dir = models_dir or os.path.join(os.path.dirname(__file__), '..', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Initialize components
        self.trader = RLTrader(actor_lr=actor_lr, critic_lr=critic_lr)
        self.reward_calculator = RewardCalculator()
        
        # Initialize trading state variables
        self.previous_positions = torch.zeros(len(PAIRS_BY_LIQUIDITY_OANDA))
        self.transaction_cost_rate = 0.0002  # 2 basis points per trade
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
            
            # Update metrics with correct keys
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
            self.previous_positions = torch.zeros(len(PAIRS_BY_LIQUIDITY_OANDA))
            
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
        for i in range(min(days, len(features) - 1)):
            # Get current state
            state = torch.tensor(features[i], dtype=torch.float32)
            
            # Get action (use mean for evaluation)
            action, _ = self.trader.get_action(state, training=False)
            
            # Calculate reward
            reward_info = self.reward_calculator.calculate_reward(
                action.detach().numpy(),
                price_changes[i]
            )
            
            # Store results
            returns.append(reward_info['portfolio_return'])
            positions.append(action.detach().numpy())
            rewards.append(reward_info['clipped_reward'])
            
            # Print daily results
            print(f"\nDay {i + 1}/{days}")
            print(f"Portfolio Return: {reward_info['portfolio_return']:.4f}")
            print(f"Reward: {reward_info['clipped_reward']:.4f}")
        
        # Calculate final metrics
        returns = np.array(returns)
        total_return = np.sum(returns)
        sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        
        return {
            'returns': returns,
            'positions': np.array(positions),
            'rewards': np.array(rewards),
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio
        }
    
    def plot_training_progress(self):
        """Plot training progress metrics."""
        plt.figure(figsize=(15, 10))
        
        # Plot rewards
        plt.subplot(2, 2, 1)
        plt.plot(self.metrics['epoch_rewards'])
        plt.title('Average Reward per Epoch')
        plt.xlabel('Epoch')
        plt.ylabel('Reward')
        
        # Plot returns
        plt.subplot(2, 2, 2)
        plt.plot(self.metrics['epoch_returns'])
        plt.title('Portfolio Return per Epoch')
        plt.xlabel('Epoch')
        plt.ylabel('Return')
        
        # Plot Sharpe ratio
        plt.subplot(2, 2, 3)
        plt.plot(self.metrics['epoch_sharpe'])
        plt.title('Differential Sharpe Ratio per Epoch')
        plt.xlabel('Epoch')
        plt.ylabel('DSR')
        
        # Plot losses
        plt.subplot(2, 2, 4)
        plt.plot(self.metrics['epoch_losses'])
        plt.title('Average Loss per Epoch')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.models_dir, 'training_progress.png'))
        plt.close()
    
    def plot_position_heatmap(self, positions: np.ndarray, title: str = 'Position Heatmap'):
        """
        Plot position heatmap showing long and short positions.
        
        Args:
            positions: Position array [n_days, n_instruments]
            title: Plot title
        """
        plt.figure(figsize=(15, 8))
        
        # Create heatmap
        sns.heatmap(positions.T, 
                   cmap='RdBu_r',  # Red for short, blue for long
                   center=0,       # Center colormap at 0
                   cbar_kws={'label': 'Position Size'})
        
        plt.title(title)
        plt.xlabel('Day')
        plt.ylabel('Instrument')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.models_dir, 'position_heatmap.png'))
        plt.close()
    
    def save_checkpoint(self, epoch: int):
        """Save training checkpoint."""
        checkpoint_path = os.path.join(self.models_dir, f'checkpoint_epoch_{epoch}.pt')
        self.trader.save_model(checkpoint_path)
        
    def load_checkpoint(self, epoch: int):
        """
        Load training checkpoint with robust compatibility handling.
        
        Args:
            epoch: Epoch number to load
        """
        checkpoint_path = os.path.join(self.models_dir, f'checkpoint_epoch_{epoch}.pt')
        
        if not os.path.exists(checkpoint_path):
            logger.error(f"Checkpoint file not found: {checkpoint_path}")
            return False
            
        logger.info(f"Loading checkpoint from epoch {epoch}...")
        
        # Use the improved load_model method that includes compatibility handling
        try:
            # Initialize networks by generating a dummy action if they haven't been initialized
            if getattr(self.trader, 'actor', None) is None or getattr(self.trader, 'critic', None) is None:
                logger.info("Initializing networks before loading checkpoint...")
                # Generate a dummy state tensor for initialization
                dummy_features = torch.zeros(1, self.trader.autoencoder.n_features if self.trader.autoencoder_loaded else 1084)
                # Get a dummy action to trigger network initialization
                self.trader.get_action(dummy_features, training=False)
        
            # Load the checkpoint with compatibility handling
            self.trader.load_model(checkpoint_path)
            logger.info(f"Successfully loaded checkpoint from epoch {epoch}")
            return True
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return False
    
    def _load_market_data(self):
        """Load market data from database."""
        logger.info("Loading market data from database...")
        
        # Load forex data
        logger.info("Loading forex data...")
        try:
            forex_data = self.load_forex_data()
            logger.info(f"Forex data loaded: {forex_data.shape if forex_data is not None else 'None'}")
        except Exception as e:
            logger.error(f"Error loading forex data: {e}")
            raise
        if forex_data is None or forex_data.empty:
            raise ValueError("Failed to load forex data")
            
        # Load ETF data
        logger.info("Loading ETF data...")
        try:
            etf_data = self.load_etf_data()
            logger.info(f"ETF data loaded: {etf_data.shape if etf_data is not None else 'None'}")
        except Exception as e:
            logger.error(f"Error loading ETF data: {e}")
            raise
        if etf_data is None or etf_data.empty:
            raise ValueError("Failed to load ETF data")
            
        # Combine forex and ETF data
        print("Combining forex and ETF data...")
        market_data = pd.concat([forex_data, etf_data], axis=1)
        
        print(f"Loaded market data shape: {market_data.shape}")
        
        # Convert to numpy arrays and create the expected dictionary structure
        features = market_data.values
        # Clean features: replace NaNs and Infs with zeros
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
            
        # Calculate price changes for each instrument with robust validation
        price_changes = np.zeros((len(market_data), len(PAIRS_BY_LIQUIDITY_OANDA)))
        missing_price_features = []
        
        for i, instrument in enumerate(PAIRS_BY_LIQUIDITY_OANDA):
            # Get the feature names for this instrument
            instrument_features = get_selected_features_per_instrument().get(instrument, [])
            if not instrument_features:
                print(f"Warning: No features found for {instrument}. Skipping returns calculation.")
                missing_price_features.append(instrument)
                continue
                
            # Special debugging for GBP_AUD
            if instrument == "GBP_AUD":
                print(f"DEBUG GBP_AUD: Got {len(instrument_features)} features")
                print(f"DEBUG GBP_AUD: First 5 features: {instrument_features[:5]}")
            
            # Find the first price-related feature for this instrument
            price_feature = next((f for f in instrument_features if any(x in f.lower() for x in ['close', 'price', 'mid'])), None)
            
            # Special handling for GBP_AUD if no price feature found
            if price_feature is None and instrument == "GBP_AUD":
                # Try to use a more generic feature name
                price_feature = "close"
                print(f"DEBUG GBP_AUD: Using generic 'close' as price feature")
                
            if price_feature is None:
                print(f"Warning: No price feature found for {instrument}. Skipping returns calculation.")
                missing_price_features.append(instrument)
                continue
                
            col_name = f"{instrument}__{price_feature}"
            
            # For GBP_AUD, try alternative column names if the standard one isn't found
            if instrument == "GBP_AUD" and col_name not in market_data.columns:
                print(f"DEBUG GBP_AUD: Column {col_name} not found")
                # Look for any column containing GBP_AUD and close/price
                gbp_aud_cols = [c for c in market_data.columns if "GBP_AUD" in c and any(x in c.lower() for x in ['close', 'price', 'mid'])]
                if gbp_aud_cols:
                    col_name = gbp_aud_cols[0]
                    print(f"DEBUG GBP_AUD: Using alternative column {col_name}")
                else:
                    print(f"DEBUG GBP_AUD: No suitable alternative columns found")
            
            if col_name not in market_data.columns:
                print(f"Warning: {col_name} not found in data columns. Skipping returns calculation for {instrument}.")
                if instrument == "GBP_AUD":
                    print(f"DEBUG GBP_AUD: Available columns starting with GBP_AUD:")
                    gbp_aud_cols = [c for c in market_data.columns if c.startswith("GBP_AUD")]
                    for c in gbp_aud_cols[:10]:  # Print first 10 columns only
                        print(f"  - {c}")
                missing_price_features.append(instrument)
                continue
                
            price_series = market_data[col_name]
            
            # Validate price series
            if price_series.isna().all() or (price_series == 0).all():
                print(f"Warning: Invalid price series for {instrument} (all NaN or zero). Skipping returns calculation.")
                missing_price_features.append(instrument)
                continue
                
            # Calculate returns with robust handling
            returns = price_series.pct_change()
            
            # Handle edge cases
            returns = returns.fillna(0)  # First row will be NaN
            returns = returns.replace([np.inf, -np.inf], 0)  # Handle division by zero
            
            # Clip extreme returns
            returns = returns.clip(-0.5, 0.5)
            
            price_changes[:, i] = returns
            
        if missing_price_features:
            print("\nSummary of missing price features:")
            for instrument in missing_price_features:
                print(f"- {instrument}")
            print("\nConsider updating feature selection for these instruments.")
        
        # Validate final price changes
        if np.isnan(price_changes).any():
            print("Warning: NaN values found in price changes after processing. Replacing with zeros.")
            price_changes = np.nan_to_num(price_changes, nan=0.0)
            
        if np.isinf(price_changes).any():
            print("Warning: Infinite values found in price changes after processing. Replacing with zeros.")
            price_changes = np.nan_to_num(price_changes, posinf=0.0, neginf=0.0)
        
        # Store missing_instruments as an instance variable for use in reward calculation
        self.missing_instruments = missing_price_features
        
        return {
            'features': features,
            'price_changes': price_changes,
            'missing_instruments': missing_price_features
        }
    
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

    def load_forex_data(self):
        """Load forex data from database."""
        logger.info("Starting forex data load from database...")
        try:
            forex_data, _ = load_instrument_data(
                target_instruments=PAIRS_BY_LIQUIDITY_OANDA,
                instrument_feature_map=get_selected_features_per_instrument(),
                table_name='forex_features',
                n_rows=50000
            )
            logger.info(f"Forex data load completed: {forex_data.shape if forex_data is not None else 'None'}")
            return forex_data
        except Exception as e:
            logger.error(f"Error in load_forex_data: {e}")
            raise

    def load_etf_data(self):
        """Load ETF data from database."""
        logger.info("Starting ETF data load from database...")
        try:
            etf_data, _ = load_instrument_data(
                target_instruments=ETF_SYMBOLS,
                instrument_feature_map=get_selected_features_per_instrument(),
                table_name='etf_features',
                n_rows=50000
        )
            logger.info(f"ETF data load completed: {etf_data.shape if etf_data is not None else 'None'}")
            return etf_data
        except Exception as e:
            logger.error(f"Error in load_etf_data: {e}")
            raise

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
                idx = PAIRS_BY_LIQUIDITY_OANDA.index(instrument)
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
    parser = argparse.ArgumentParser(description='Trading System')
    parser.add_argument('--train', action='store_true', help='Train the policy network')
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--eval', action='store_true', help='Evaluate the policy network')
    parser.add_argument('--sim', action='store_true', help='Run a trading simulation')
    parser.add_argument('--sim-days', type=int, default=20, help='Number of days to simulate')
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    logger.info("Starting Trading System")
    logger.info(f"Arguments: {args}")
    
    # Create trading system
    logger.info("Creating TradingSystem instance...")
    system = TradingSystem(train_on_startup=False)
    logger.info("TradingSystem created successfully")
    
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
        system.plot_position_heatmap(sim_results['positions'], '30-Day Trading Simulation')
    
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
        print("\nCurrent Positions:")
        for i, pair in enumerate(PAIRS_BY_LIQUIDITY_OANDA):
            print(f"{pair}: {signals['positions'][-1][i]:.4f}")
        
        # Print portfolio metrics
        print("\nPortfolio Metrics:")
        print(f"Total Return: {signals['total_return']:.4f}")
        print(f"Sharpe Ratio: {signals['sharpe_ratio']:.4f}")

if __name__ == "__main__":
    main() 