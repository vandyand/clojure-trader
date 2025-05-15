#!/usr/bin/env python
"""
Script to evaluate the latest trained model checkpoint and generate detailed performance reports.
Uses the compatibility module to ensure robust checkpoint loading.
"""
import os
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt
import glob
import re
import seaborn as sns
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.trading_system import TradingSystem
from rl.checkpoint_compat import fix_checkpoint_loading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"eval_latest_{os.path.basename(__file__).split('.')[0]}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ModelEvaluation")

def find_latest_checkpoint(models_dir="models", min_epoch=None, max_epoch=None) -> Tuple[Optional[str], Optional[int]]:
    """
    Find the latest checkpoint file within optional epoch bounds.
    
    Args:
        models_dir: Directory containing model checkpoints
        min_epoch: Minimum epoch to consider (inclusive)
        max_epoch: Maximum epoch to consider (inclusive)
        
    Returns:
        Tuple of (checkpoint_path, epoch_number) or (None, None) if no valid checkpoint found
    """
    checkpoint_pattern = os.path.join(models_dir, "checkpoint_epoch_*.pt")
    checkpoint_files = glob.glob(checkpoint_pattern)
    
    if not checkpoint_files:
        logger.warning(f"No checkpoint files found matching pattern: {checkpoint_pattern}")
        return None, None
    
    # Extract epoch numbers and find the max
    epochs_with_files = []
    for f in checkpoint_files:
        match = re.search(r'epoch_(\d+)\.pt', f)
        if match:
            epoch = int(match.group(1))
            # Apply epoch filters if provided
            if (min_epoch is None or epoch >= min_epoch) and (max_epoch is None or epoch <= max_epoch):
                epochs_with_files.append((epoch, f))
    
    if not epochs_with_files:
        logger.warning(f"No checkpoints found within epoch range {min_epoch} to {max_epoch}")
        return None, None
    
    # Sort by epoch number and get the latest
    latest_epoch, latest_file = sorted(epochs_with_files, key=lambda x: x[0], reverse=True)[0]
    return latest_file, latest_epoch

def initialize_trading_system() -> TradingSystem:
    """
    Initialize a trading system with proper error handling.
    
    Returns:
        Initialized TradingSystem
    """
    try:
        # Create trading system
        logger.info("Initializing trading system...")
        system = TradingSystem()
        
        # Load market data to initialize model structures
        logger.info("Loading market data for initialization...")
        test_data = system._load_market_data()
        
        # Initialize the networks by running a single evaluation step
        if test_data and 'features' in test_data and len(test_data['features']) > 0:
            logger.info("Initializing model networks...")
            state = torch.tensor(test_data['features'][0], dtype=torch.float32)
            system.trader.get_action(state, training=False)
            logger.info("Network initialization successful")
        else:
            logger.warning("Could not initialize networks with market data - using dummy data")
            # Create dummy data for initialization
            if system.trader.autoencoder_loaded:
                n_features = system.trader.autoencoder.n_features
            else:
                n_features = 1084  # Default
            dummy_features = torch.zeros(1, n_features)
            system.trader.get_action(dummy_features, training=False)
            
        return system, test_data
    
    except Exception as e:
        logger.error(f"Error initializing trading system: {e}")
        raise

def evaluate_latest_model(n_episodes=50, episode_length=1000, min_epoch=None, max_epoch=None):
    """
    Evaluate the latest model checkpoint with thorough evaluation.
    
    Args:
        n_episodes: Number of episodes to evaluate
        episode_length: Length of each episode
        min_epoch: Minimum epoch to consider (inclusive)
        max_epoch: Maximum epoch to consider (inclusive)
        
    Returns:
        Evaluation results dictionary
    """
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    
    # Find latest checkpoint
    latest_checkpoint, latest_epoch = find_latest_checkpoint(
        models_dir=models_dir,
        min_epoch=min_epoch,
        max_epoch=max_epoch
    )
    
    if not latest_checkpoint:
        logger.error("No checkpoint found. Please train the model first.")
        return None
    
    logger.info(f"Found latest checkpoint: {latest_checkpoint} (Epoch {latest_epoch})")
    
    try:
        # Initialize trading system and load data
        system, test_data = initialize_trading_system()
        
        # Load the checkpoint
        logger.info(f"Loading checkpoint from epoch {latest_epoch}...")
        load_success = system.load_checkpoint(latest_epoch)
        
        if not load_success:
            logger.warning("Standard checkpoint loading failed, trying manual compatibility fixing...")
            # If the standard loading fails, try to use the compatibility module directly
            if hasattr(system.trader, 'actor') and system.trader.actor is not None:
                actor_fixed = fix_checkpoint_loading(system.trader.actor, latest_checkpoint)
                critic_fixed = fix_checkpoint_loading(system.trader.critic, latest_checkpoint)
                
                if actor_fixed and critic_fixed:
                    logger.info("Successfully fixed checkpoint loading with compatibility module")
                else:
                    logger.error("Failed to load checkpoint even with compatibility module")
                    return None
            else:
                logger.error("Cannot fix checkpoint loading - actor/critic networks not initialized")
                return None
        
        # Run thorough evaluation
        logger.info(f"Running evaluation with {n_episodes} episodes, each {episode_length} steps...")
        eval_results = system.evaluate(
            test_data=test_data, 
            n_episodes=n_episodes, 
            episode_length=episode_length
        )
        
        # Print detailed evaluation results
        logger.info("\n---------- EVALUATION RESULTS ----------")
        logger.info(f"Total Return: {eval_results['total_return']:.4f}")
        logger.info(f"Sharpe Ratio: {eval_results['sharpe_ratio']:.4f}")
        logger.info(f"Maximum Drawdown: {eval_results['max_drawdown']:.4f}")
        logger.info(f"Win Rate: {eval_results.get('win_rate', 0):.4f}")
        logger.info(f"Average Trade Return: {eval_results.get('avg_trade_return', 0):.6f}")
        logger.info("-----------------------------------------")
        
        # Generate position heatmap
        if 'positions' in eval_results and len(eval_results['positions']) > 0:
            logger.info("\nGenerating position heatmap...")
            positions = eval_results['positions']
            plt.figure(figsize=(15, 8))
            
            # Create heatmap
            positions_array = np.array(positions)
            display_positions = positions_array[-100:].T if len(positions_array) > 100 else positions_array.T
            
            sns.heatmap(display_positions, 
                       cmap='RdBu_r',  # Red for short, blue for long
                       center=0,       # Center colormap at 0
                       cbar_kws={'label': 'Position Size'})
            
            plt.title(f'Position Heatmap (Epoch {latest_epoch})')
            plt.xlabel('Time Step')
            plt.ylabel('Instrument')
            
            plt.tight_layout()
            plt.savefig(os.path.join(models_dir, 'latest_position_heatmap.png'), dpi=300)
            logger.info(f"Saved position heatmap to {os.path.join(models_dir, 'latest_position_heatmap.png')}")
        else:
            logger.warning("No position data available for heatmap generation")
        
        return eval_results
    
    except Exception as e:
        logger.error(f"Error in evaluation: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate latest model checkpoint")
    parser.add_argument('--episodes', type=int, default=30, help='Number of episodes to evaluate')
    parser.add_argument('--length', type=int, default=1000, help='Length of each episode')
    parser.add_argument('--min-epoch', type=int, help='Minimum epoch to consider')
    parser.add_argument('--max-epoch', type=int, help='Maximum epoch to consider')
    
    args = parser.parse_args()
    
    logger.info(f"Starting evaluation with {args.episodes} episodes of length {args.length}")
    
    results = evaluate_latest_model(
        n_episodes=args.episodes,
        episode_length=args.length,
        min_epoch=args.min_epoch,
        max_epoch=args.max_epoch
    )
    
    if results:
        logger.info("Evaluation completed successfully")
    else:
        logger.error("Evaluation failed")
        sys.exit(1) 