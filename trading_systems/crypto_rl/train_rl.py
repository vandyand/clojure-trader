#!/usr/bin/env python
"""
Training script for the Crypto RL Trading System.
"""
import os
import sys
import argparse
import torch
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_rl.trading_system import CryptoTradingSystem
from crypto_rl.data_fetcher import CryptoMarketDataFetcher
from crypto_rl.constants import CRYPTO_PAIRS_BY_LIQUIDITY, ETF_SYMBOLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"crypto_rl_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CryptoRLTraining")

def train_crypto_rl_system(
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    save_interval: int = 10,
    models_dir: str = None
):
    """
    Train the crypto RL trading system.
    
    Args:
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate for the policy network
        save_interval: Interval for saving checkpoints
        models_dir: Directory to save models
    """
    logger.info("Starting Crypto RL Training")
    logger.info(f"Epochs: {epochs}, Batch Size: {batch_size}, Learning Rate: {learning_rate}")
    
    # Create trading system
    system = CryptoTradingSystem(
        models_dir=models_dir,
        actor_lr=learning_rate,
        critic_lr=learning_rate * 10,  # Critic typically uses higher learning rate
        train_on_startup=False
    )
    
    # Train the system
    logger.info("Starting training...")
    system.train(epochs=epochs, batch_size=batch_size)
    
    # Plot training progress
    logger.info("Plotting training progress...")
    system.plot_training_progress()
    
    # Evaluate the trained model on out-of-sample data
    logger.info("Evaluating trained model on out-of-sample data...")
    logger.info("This evaluation uses different data than training to test generalization.")
    logger.info("The results may differ from training metrics due to overfitting.")
    eval_results = system.evaluate(n_episodes=50, episode_length=500)
    
    logger.info("Training completed!")
    logger.info(f"Final Evaluation Results (Out-of-Sample):")
    logger.info(f"  Total Return: {eval_results['total_return']:.6f}")
    logger.info(f"  Sharpe Ratio: {eval_results['sharpe_ratio']:.4f}")
    logger.info(f"  Max Drawdown: {eval_results['max_drawdown']:.4f}")
    logger.info(f"  Win Rate: {eval_results['win_rate']:.4f}")
    logger.info(f"  Average Return per Episode: {eval_results['avg_return']:.6f}")
    
    return system, eval_results

def test_data_fetcher():
    """Test the data fetcher to ensure it's working correctly."""
    logger.info("Testing data fetcher...")
    
    try:
        fetcher = CryptoMarketDataFetcher()
        
        # Test with a few instruments
        test_instruments = ["BTCUSDT", "ETHUSDT", "SPY", "QQQ"]
        
        for instrument in test_instruments:
            logger.info(f"Testing {instrument}...")
            
            # Get price data
            price_data = fetcher.fetch_price_data(instrument)
            if price_data is not None:
                logger.info(f"  Price data shape: {price_data.shape}")
                logger.info(f"  Latest close: {price_data['close'].iloc[-1]:.4f}")
            else:
                logger.warning(f"  No price data for {instrument}")
            
            # Get features
            features = fetcher.calculate_instrument_features(instrument)
            if features is not None:
                logger.info(f"  Features shape: {features.shape}")
                logger.info(f"  Number of features: {len(features.columns)}")
            else:
                logger.warning(f"  No features for {instrument}")
        
        # Test feature vector preparation
        logger.info("Testing feature vector preparation...")
        feature_vector = fetcher.prepare_feature_vector()
        if feature_vector is not None:
            logger.info(f"Feature vector shape: {feature_vector.shape}")
            logger.info(f"Feature vector sample: {feature_vector[:10]}")
        else:
            logger.error("Failed to prepare feature vector")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing data fetcher: {e}")
        return False

def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train Crypto RL Trading System')
    parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for training')
    parser.add_argument('--lr', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--save-interval', type=int, default=10, help='Save interval')
    parser.add_argument('--test-data', action='store_true', help='Test data fetcher before training')
    parser.add_argument('--models-dir', type=str, default=None, help='Models directory')
    
    args = parser.parse_args()
    
    logger.info("Crypto RL Training Script")
    logger.info(f"Arguments: {args}")
    
    # Test data fetcher if requested
    if args.test_data:
        logger.info("Testing data fetcher...")
        if not test_data_fetcher():
            logger.error("Data fetcher test failed. Exiting.")
            return
    
    # Train the system
    try:
        system, eval_results = train_crypto_rl_system(
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            save_interval=args.save_interval,
            models_dir=args.models_dir
        )
        
        logger.info("Training completed successfully!")
        
        # Save final results
        results = {
            'training_completed': True,
            'epochs': args.epochs,
            'batch_size': args.batch_size,
            'learning_rate': args.lr,
            'evaluation_results': eval_results,
            'timestamp': datetime.now().isoformat()
        }
        
        results_file = f"crypto_rl_training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            import json
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {results_file}")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

if __name__ == "__main__":
    main() 