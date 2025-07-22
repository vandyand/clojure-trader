"""
Unified Futures Trading System

Main integration module that combines:
1. Feature engineering (Fibonacci + ETF + crypto technical indicators)
2. Fusion autoencoder for state representation
3. RL policy network for position sizing
4. Advanced reward calculation with differential Sharpe ratio
5. Support for both long and short positions

This system trades 20 crypto perpetual futures pairs using sophisticated
multi-market feature fusion and advanced risk management.
"""

import os
import sys
import argparse
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import logging
from datetime import datetime, timedelta
import seaborn as sns
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_futures_rl.feature_engineering import UnifiedFeatureEngineer
from unified_futures_rl.autoencoder import FusionAutoencoder, AutoencoderTrainer
from unified_futures_rl.policy_network import UnifiedFuturesTrader
from unified_futures_rl.reward_calculator import RewardCalculator
from unified_futures_rl.data_fetcher import UnifiedFuturesDataFetcher
from unified_futures_rl.constants import (
    CRYPTO_FUTURES_PAIRS, ETF_SYMBOLS, TOTAL_INPUT_FEATURES,
    AUTOENCODER_BOTTLENECK_DIM, BATCH_SIZE, ACCOUNT_SIZE,
    MAX_LEVERAGE, TRANSACTION_COST_RATE
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"unified_futures_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedFuturesTrading")

class UnifiedFuturesTradingSystem:
    """
    High-level interface for the unified futures trading system.
    """
    
    def __init__(self, 
                models_dir: str = None, 
                autoencoder_path: str = None,
                trader_path: str = None,
                train_on_startup: bool = False):
        
        self.models_dir = models_dir or os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Initialize components
        self.feature_engineer = UnifiedFeatureEngineer()
        self.reward_calculator = RewardCalculator()
        self.data_fetcher = UnifiedFuturesDataFetcher(
            crypto_pairs=CRYPTO_FUTURES_PAIRS,
            etf_symbols=ETF_SYMBOLS,
            history_days=1500  # Increased to ensure 1000+ candles
        )
        
        # Initialize trading state
        self.previous_positions = np.zeros(len(CRYPTO_FUTURES_PAIRS))
        self.current_portfolio_value = ACCOUNT_SIZE
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
            'epoch_entropy': [],
            'position_diversity': []
        }
        
        # Load or initialize trader
        self.trader = UnifiedFuturesTrader(
            autoencoder_path=autoencoder_path,
            n_instruments=len(CRYPTO_FUTURES_PAIRS)
        )
        
        # Load existing trader if path provided
        if trader_path and os.path.exists(trader_path):
            self.trader.load_model(trader_path)
            logger.info(f"Loaded existing trader from {trader_path}")
        
        if train_on_startup:
            self.train()
    
    def train(self, epochs: int = 100, batch_size: int = BATCH_SIZE):
        """
        Train the unified futures trading system.
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
        """
        self.is_training = True
        self.current_epoch = 0
        self.total_epochs = epochs
        
        # Load real market data
        logger.info("Fetching real market data from Bitunix API and yfinance...")
        market_data = self.data_fetcher.fetch_all_data()
        
        # Validate data quality
        crypto_validation = self.data_fetcher.validate_data_quality(market_data['crypto'])
        etf_validation = self.data_fetcher.validate_data_quality(market_data['etf'])
        
        # Log validation results
        valid_crypto = sum(1 for result in crypto_validation.values() if result['valid'])
        valid_etfs = sum(1 for result in etf_validation.values() if result['valid'])
        
        logger.info(f"Data validation: {valid_crypto}/{len(CRYPTO_FUTURES_PAIRS)} crypto pairs, {valid_etfs}/{len(ETF_SYMBOLS)} ETFs")
        
        if valid_crypto == 0:
            logger.error("No valid crypto data available. Cannot proceed with training.")
            return
        
        # Training loop
        for epoch in range(epochs):
            self.current_epoch = epoch
            epoch_metrics = self._train_epoch(market_data, batch_size)
            
            # Update metrics
            self.metrics['epoch_rewards'].append(epoch_metrics['reward'])
            self.metrics['epoch_returns'].append(epoch_metrics['return'])
            self.metrics['epoch_sharpe'].append(epoch_metrics['sharpe'])
            self.metrics['epoch_losses'].append(epoch_metrics['loss'])
            self.metrics['epoch_entropy'].append(epoch_metrics['entropy'])
            self.metrics['position_diversity'].append(epoch_metrics['position_diversity'])
            
            # Log progress
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}/{epochs}: "
                          f"Reward={epoch_metrics['reward']:.4f}, "
                          f"Return={epoch_metrics['return']:.4f}, "
                          f"Sharpe={epoch_metrics['sharpe']:.4f}")
            
            # Save checkpoint
            if epoch % 20 == 0:
                self.save_checkpoint(epoch)
        
        self.is_training = False
        logger.info("Training completed")
    
    def evaluate(self, test_data: Dict = None, n_episodes: int = 100, 
                episode_length: int = 1000) -> Dict[str, float]:
        """
        Evaluate the trained trading system.
        
        Args:
            test_data: Test market data
            n_episodes: Number of evaluation episodes
            episode_length: Length of each episode
            
        Returns:
            Evaluation metrics
        """
        if test_data is None:
            logger.info("Fetching test data from Bitunix API and yfinance...")
            test_data = self.data_fetcher.fetch_all_data()
        
        episode_returns = []
        episode_sharpes = []
        episode_drawdowns = []
        
        for episode in range(n_episodes):
            # Reset state
            self.reward_calculator.reset_state()
            self.previous_positions = np.zeros(len(CRYPTO_FUTURES_PAIRS))
            portfolio_values = [ACCOUNT_SIZE]
            
            # Run episode
            for step in range(episode_length):
                # Get current state
                current_features = self._get_current_features(test_data, step)
                
                # Get action
                state_tensor = torch.FloatTensor(current_features).unsqueeze(0)
                actions, _ = self.trader.get_action(state_tensor, training=False)
                actions = actions.cpu().numpy().squeeze()
                
                # Get real price changes
                price_changes = self._get_price_changes(test_data, step)
                
                # Calculate reward
                reward_info = self.reward_calculator.calculate_reward(
                    actions, price_changes, self.previous_positions
                )
                
                # Update portfolio value
                portfolio_return = reward_info['portfolio_return']
                new_value = portfolio_values[-1] * (1 + portfolio_return)
                portfolio_values.append(new_value)
                
                # Update previous positions
                self.previous_positions = reward_info['final_positions']
            
            # Calculate episode metrics
            returns = np.diff(portfolio_values) / portfolio_values[:-1]
            episode_returns.append(np.sum(returns))
            
            if len(returns) > 1:
                sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
                episode_sharpes.append(sharpe)
            
            drawdown = self._calculate_max_drawdown(portfolio_values)
            episode_drawdowns.append(drawdown)
        
        return {
            'mean_return': np.mean(episode_returns),
            'std_return': np.std(episode_returns),
            'mean_sharpe': np.mean(episode_sharpes),
            'mean_drawdown': np.mean(episode_drawdowns),
            'win_rate': np.mean([r > 0 for r in episode_returns])
        }
    
    def generate_trading_signals(self, 
                               crypto_data: Dict[str, pd.DataFrame],
                               etf_data: Dict[str, pd.DataFrame],
                               days: int = 30) -> Dict[str, np.ndarray]:
        """
        Generate current trading signals.
        
        Args:
            crypto_data: Current crypto market data
            etf_data: Current ETF market data
            days: Number of days to simulate
            
        Returns:
            Dictionary with position signals and confidence scores
        """
        # Engineer features
        features = self.feature_engineer.engineer_features(crypto_data, etf_data)
        features = self.feature_engineer.normalize_features(features)
        
        # Get position signals
        state_tensor = torch.FloatTensor(features).unsqueeze(0)
        position_signals = self.trader.get_position_signals(state_tensor)
        confidence_scores = self.trader.get_position_confidence(state_tensor)
        
        # Calculate reward info for analysis (using latest price changes)
        latest_prices = self.data_fetcher.get_latest_prices()
        price_changes = []
        for pair in CRYPTO_FUTURES_PAIRS:
            if pair in latest_prices:
                # Calculate simple return from previous position
                current_price = latest_prices[pair]
                # For now, use a small random change (in real trading, this would be actual price changes)
                price_changes.append(np.random.randn() * 0.01)
            else:
                price_changes.append(0.0)
        
        price_changes = np.array(price_changes)
        reward_info = self.reward_calculator.calculate_reward(
            position_signals, price_changes, self.previous_positions
        )
        
        return {
            'position_signals': position_signals,
            'confidence_scores': confidence_scores,
            'final_positions': reward_info['final_positions'],
            'portfolio_return': reward_info['portfolio_return'],
            'differential_sharpe': reward_info['differential_sharpe'],
            'position_entropy': reward_info['position_entropy'],
            'alpha_0': reward_info['alpha_0']
        }
    
    def plot_training_progress(self):
        """Plot training progress metrics."""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # Rewards
        axes[0, 0].plot(self.metrics['epoch_rewards'])
        axes[0, 0].set_title('Training Rewards')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Reward')
        
        # Returns
        axes[0, 1].plot(self.metrics['epoch_returns'])
        axes[0, 1].set_title('Portfolio Returns')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Return')
        
        # Sharpe ratios
        axes[0, 2].plot(self.metrics['epoch_sharpe'])
        axes[0, 2].set_title('Sharpe Ratios')
        axes[0, 2].set_xlabel('Epoch')
        axes[0, 2].set_ylabel('Sharpe')
        
        # Losses
        axes[1, 0].plot(self.metrics['epoch_losses'])
        axes[1, 0].set_title('Training Losses')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Loss')
        
        # Entropy
        axes[1, 1].plot(self.metrics['epoch_entropy'])
        axes[1, 1].set_title('Position Entropy')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Entropy')
        
        # Position diversity
        axes[1, 2].plot(self.metrics['position_diversity'])
        axes[1, 2].set_title('Position Diversity')
        axes[1, 2].set_xlabel('Epoch')
        axes[1, 2].set_ylabel('Diversity')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.models_dir, 'training_progress.png'))
        plt.show()
    
    def plot_position_heatmap(self, positions: np.ndarray, title: str = 'Position Heatmap'):
        """Plot position heatmap."""
        plt.figure(figsize=(12, 6))
        
        # Create heatmap
        position_matrix = positions.reshape(1, -1)
        sns.heatmap(position_matrix, 
                   xticklabels=CRYPTO_FUTURES_PAIRS,
                   yticklabels=['Positions'],
                   cmap='RdYlGn',
                   center=0,
                   annot=True,
                   fmt='.3f')
        
        plt.title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.models_dir, 'position_heatmap.png'))
        plt.show()
    
    def save_checkpoint(self, epoch: int):
        """Save training checkpoint."""
        checkpoint_path = os.path.join(self.models_dir, f'checkpoint_epoch_{epoch}.pt')
        self.trader.save_model(checkpoint_path)
        
        # Save metrics (convert numpy types to Python native types for JSON serialization)
        metrics_path = os.path.join(self.models_dir, f'metrics_epoch_{epoch}.json')
        with open(metrics_path, 'w') as f:
            # Convert numpy types to Python native types
            json_metrics = {}
            for key, value in self.metrics.items():
                if isinstance(value, list):
                    json_metrics[key] = [float(v) if hasattr(v, 'item') else v for v in value]
                else:
                    json_metrics[key] = float(value) if hasattr(value, 'item') else value
            json.dump(json_metrics, f, indent=2)
    
    def load_checkpoint(self, epoch: int):
        """Load training checkpoint."""
        checkpoint_path = os.path.join(self.models_dir, f'checkpoint_epoch_{epoch}.pt')
        if os.path.exists(checkpoint_path):
            self.trader.load_model(checkpoint_path)
            
            # Load metrics
            metrics_path = os.path.join(self.models_dir, f'metrics_epoch_{epoch}.json')
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r') as f:
                    self.metrics = json.load(f)
            
            logger.info(f"Loaded checkpoint from epoch {epoch}")
        else:
            logger.warning(f"Checkpoint for epoch {epoch} not found")
    
    def _load_market_data(self) -> Dict:
        """
        Load real market data for training.
        
        Returns:
            Dictionary with crypto and ETF data
        """
        return self.data_fetcher.fetch_all_data()
    
    def _train_epoch(self, market_data: Dict, batch_size: int) -> Dict[str, float]:
        """
        Train for one epoch (optimized for speed).
        
        Args:
            market_data: Market data dictionary
            batch_size: Batch size for training
            
        Returns:
            Epoch metrics
        """
        epoch_rewards = []
        epoch_returns = []
        epoch_sharpes = []
        epoch_losses = []
        epoch_entropy = []
        epoch_position_diversity = []
        
        # Calculate minimum data length across all pairs to avoid index errors
        min_crypto_length = min(len(market_data['crypto'][pair]) for pair in CRYPTO_FUTURES_PAIRS)
        min_etf_length = min(len(market_data['etf'][symbol]) for symbol in ETF_SYMBOLS)
        min_data_length = min(min_crypto_length, min_etf_length)
        
        # Use minimum data length minus 1 to allow for next state calculation
        n_samples = min(1000, min_data_length - 1)  # Number of training samples per epoch
        
        logger.info(f"Training with {n_samples} samples (min data length: {min_data_length})")
        
        # Pre-compute all features for the entire epoch (MASSIVE SPEEDUP)
        logger.info("Pre-computing features for entire epoch...")
        all_features = []
        all_price_changes = []
        
        # Use vectorized operations where possible
        for step in range(n_samples + 1):  # +1 for next states
            features = self._get_current_features(market_data, step)
            all_features.append(features)
            
            if step < n_samples:  # Don't compute price changes for the last step
                price_changes = self._get_price_changes(market_data, step)
                all_price_changes.append(price_changes)
        
        # Convert to numpy arrays for faster access
        all_features = np.array(all_features)
        all_price_changes = np.array(all_price_changes)
        
        logger.info(f"Feature computation complete. Shape: {all_features.shape}")
        
        for batch in range(0, n_samples, batch_size):
            batch_size_actual = min(batch_size, n_samples - batch)
            
            # Generate batch data (vectorized)
            batch_states = all_features[batch:batch + batch_size_actual]
            batch_next_states = all_features[batch + 1:batch + batch_size_actual + 1]
            batch_price_changes = all_price_changes[batch:batch + batch_size_actual]
            
            # Get actions for entire batch at once
            states_tensor = torch.FloatTensor(batch_states)
            actions_batch, _ = self.trader.get_action(states_tensor)
            actions = actions_batch.cpu().numpy()
            
            # Calculate rewards for entire batch
            rewards = []
            batch_returns = []
            batch_sharpes = []
            batch_entropy = []
            
            for i in range(batch_size_actual):
                reward_info = self.reward_calculator.calculate_reward(
                    actions[i], batch_price_changes[i], self.previous_positions
                )
                
                rewards.append(reward_info['clipped_reward'])
                batch_returns.append(reward_info['portfolio_return'])
                batch_sharpes.append(reward_info['actual_sharpe'])  # Use actual Sharpe ratio
                batch_entropy.append(reward_info['position_entropy'])
                
                # Update previous positions
                self.previous_positions = reward_info['final_positions']
            
            # Convert to tensors (already optimized)
            states = torch.FloatTensor(batch_states)
            actions_tensor = torch.FloatTensor(actions)
            rewards = torch.FloatTensor(np.array(rewards))
            next_states = torch.FloatTensor(batch_next_states)
            dones = torch.FloatTensor(np.zeros(batch_size_actual))  # All zeros for continuous training
            
            # Update policy
            metrics = self.trader.update_policy(
                states=states,
                actions=actions_tensor,
                rewards=rewards,
                next_states=next_states,
                dones=dones
            )
            
            epoch_rewards.extend(rewards.tolist())
            epoch_returns.extend(batch_returns)
            epoch_sharpes.extend(batch_sharpes)
            epoch_entropy.extend(batch_entropy)
            epoch_losses.append(metrics['total_loss'])
            
            # Calculate position diversity
            position_diversity = np.std(actions, axis=1).mean()
            epoch_position_diversity.append(position_diversity)
        
        return {
            'reward': np.mean(epoch_rewards),
            'return': np.mean(epoch_returns),
            'sharpe': np.mean(epoch_sharpes),
            'loss': np.mean(epoch_losses),
            'entropy': np.mean(epoch_entropy),
            'position_diversity': np.mean(epoch_position_diversity)
        }
    
    def _get_current_features(self, market_data: Dict, step: int) -> np.ndarray:
        """Get current feature vector."""
        # Extract data up to current step
        crypto_data = {}
        etf_data = {}
        
        for pair in CRYPTO_FUTURES_PAIRS:
            if pair in market_data['crypto']:
                # Check bounds to avoid index errors
                data_length = len(market_data['crypto'][pair])
                end_idx = min(step + 1, data_length)
                crypto_data[pair] = market_data['crypto'][pair].iloc[:end_idx]
        
        for symbol in ETF_SYMBOLS:
            if symbol in market_data['etf']:
                # Check bounds to avoid index errors
                data_length = len(market_data['etf'][symbol])
                end_idx = min(step + 1, data_length)
                etf_data[symbol] = market_data['etf'][symbol].iloc[:end_idx]
        
        # Engineer features
        features = self.feature_engineer.engineer_features(crypto_data, etf_data)
        features = self.feature_engineer.normalize_features(features)
        
        return features
    
    def _get_price_changes(self, market_data: Dict, step: int) -> np.ndarray:
        """Get price changes for current step (optimized)."""
        if step == 0:
            return np.zeros(len(CRYPTO_FUTURES_PAIRS))
        
        price_changes = []
        
        for pair in CRYPTO_FUTURES_PAIRS:
            if pair in market_data['crypto']:
                # Check bounds to avoid index errors
                data_length = len(market_data['crypto'][pair])
                if step < data_length and step - 1 < data_length:
                    current_price = market_data['crypto'][pair]['close'].iloc[step]
                    previous_price = market_data['crypto'][pair]['close'].iloc[step-1]
                    change = (current_price - previous_price) / previous_price if previous_price > 0 else 0.0
                    price_changes.append(change)
                else:
                    price_changes.append(0.0)
            else:
                price_changes.append(0.0)
        
        return np.array(price_changes)
    
    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """Calculate maximum drawdown from portfolio values."""
        portfolio_values = np.array(portfolio_values)
        running_max = np.maximum.accumulate(portfolio_values)
        drawdown = (running_max - portfolio_values) / running_max
        return np.max(drawdown)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Unified Futures Trading System')
    parser.add_argument('--train', action='store_true', help='Train the system')
    parser.add_argument('--eval', action='store_true', help='Evaluate the system')
    parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help='Batch size')
    parser.add_argument('--autoencoder-path', type=str, help='Path to pre-trained autoencoder')
    parser.add_argument('--trader-path', type=str, help='Path to pre-trained trader')
    parser.add_argument('--models-dir', type=str, help='Directory to save models')
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Create trading system
    trading_system = UnifiedFuturesTradingSystem(
        models_dir=args.models_dir,
        autoencoder_path=args.autoencoder_path,
        trader_path=args.trader_path
    )
    
    if args.train:
        logger.info("Starting training...")
        trading_system.train(epochs=args.epochs, batch_size=args.batch_size)
        trading_system.plot_training_progress()
    
    if args.eval:
        logger.info("Starting evaluation...")
        eval_metrics = trading_system.evaluate()
        logger.info(f"Evaluation results: {eval_metrics}")
    
    logger.info("Trading system completed")

if __name__ == "__main__":
    main() 