#!/usr/bin/env python
"""
Script to evaluate RLTrader checkpoints from different epochs and plot performance metrics.
This allows us to see how the model performance changes over the course of training.
"""
import os
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt
import glob
import re
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.trading_system import TradingSystem

def extract_epoch_number(checkpoint_path):
    """Extract epoch number from checkpoint path."""
    match = re.search(r'epoch_(\d+)\.pt', checkpoint_path)
    if match:
        return int(match.group(1))
    return 0

def find_checkpoints(models_dir="models", n_checkpoints=10):
    """Find checkpoint files and select a subset for evaluation."""
    checkpoint_pattern = os.path.join(models_dir, "checkpoint_epoch_*.pt")
    checkpoint_files = glob.glob(checkpoint_pattern)
    
    if not checkpoint_files:
        print(f"No checkpoint files found matching pattern: {checkpoint_pattern}")
        return []
    
    # Sort by epoch number
    checkpoint_files = sorted(checkpoint_files, key=extract_epoch_number)
    
    # If we have more checkpoints than requested, select a representative subset
    if len(checkpoint_files) > n_checkpoints:
        # Choose evenly spaced checkpoints
        indices = np.linspace(0, len(checkpoint_files) - 1, n_checkpoints, dtype=int)
        selected_checkpoints = [checkpoint_files[i] for i in indices]
    else:
        selected_checkpoints = checkpoint_files
    
    return selected_checkpoints

def evaluate_checkpoint(checkpoint_path, n_episodes=20, episode_length=500):
    """Evaluate a specific checkpoint."""
    try:
        epoch = extract_epoch_number(checkpoint_path)
        print(f"\nEvaluating checkpoint from epoch {epoch}...")
        
        # Create trading system and initialize networks
        system = TradingSystem()
        
        # Load market data to initialize model
        test_data = system._load_market_data()
        
        # Initialize the networks by running a single evaluation step
        print("Initializing networks...")
        state = torch.tensor(test_data['features'][0], dtype=torch.float32)
        system.trader.get_action(state, training=False)
        
        # Now we can load the checkpoint
        print(f"Loading checkpoint from epoch {epoch}...")
        system.load_checkpoint(epoch)
        
        # Evaluate
        print(f"Running evaluation with {n_episodes} episodes...")
        eval_results = system.evaluate(test_data=test_data, n_episodes=n_episodes, episode_length=episode_length)
        
        # Add epoch number to results
        eval_results['epoch'] = epoch
        
        return eval_results
    except Exception as e:
        print(f"Error evaluating checkpoint {checkpoint_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def evaluate_multiple_checkpoints(checkpoint_files, n_episodes=20, episode_length=500):
    """Evaluate multiple checkpoints and collect results."""
    evaluation_results = []
    
    for checkpoint_file in checkpoint_files:
        result = evaluate_checkpoint(checkpoint_file, n_episodes, episode_length)
        if result:
            evaluation_results.append(result)
    
    return evaluation_results

def plot_evaluation_metrics(evaluation_results, save_dir="models"):
    """Plot evaluation metrics across epochs."""
    if not evaluation_results:
        print("No evaluation results to plot.")
        return
    
    # Extract epochs and metrics
    epochs = [result['epoch'] for result in evaluation_results]
    
    # Set up plot style
    sns.set(style="darkgrid", font_scale=1.2)
    
    # Create figure for all metrics
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('RLTrader Evaluation Results Across Training', fontsize=16)
    
    # Flatten axes for easier indexing
    axes = axes.flatten()
    
    # Plot total return
    total_returns = [result['total_return'] for result in evaluation_results]
    axes[0].plot(epochs, total_returns, 'o-', linewidth=2, markersize=8, color='green')
    axes[0].set_title('Total Return')
    axes[0].set_xlabel('Training Epoch')
    axes[0].set_ylabel('Return')
    axes[0].grid(True, linestyle='--', alpha=0.7)
    
    # Plot Sharpe ratio
    sharpe_ratios = [result['sharpe_ratio'] for result in evaluation_results]
    axes[1].plot(epochs, sharpe_ratios, 'o-', linewidth=2, markersize=8, color='blue')
    axes[1].set_title('Sharpe Ratio')
    axes[1].set_xlabel('Training Epoch')
    axes[1].set_ylabel('Ratio')
    axes[1].grid(True, linestyle='--', alpha=0.7)
    
    # Plot max drawdown
    max_drawdowns = [result['max_drawdown'] for result in evaluation_results]
    axes[2].plot(epochs, max_drawdowns, 'o-', linewidth=2, markersize=8, color='red')
    axes[2].set_title('Maximum Drawdown')
    axes[2].set_xlabel('Training Epoch')
    axes[2].set_ylabel('Drawdown')
    axes[2].grid(True, linestyle='--', alpha=0.7)
    
    # Plot win rate
    win_rates = [result.get('win_rate', 0) for result in evaluation_results]
    axes[3].plot(epochs, win_rates, 'o-', linewidth=2, markersize=8, color='purple')
    axes[3].set_title('Win Rate')
    axes[3].set_xlabel('Training Epoch')
    axes[3].set_ylabel('Rate')
    # Set y-axis limit for win rate between 0 and 1
    axes[3].set_ylim([0, 1])
    axes[3].grid(True, linestyle='--', alpha=0.7)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust to make room for suptitle
    
    # Save the plot
    save_path = os.path.join(save_dir, 'evaluation_metrics.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved evaluation metrics plot to {save_path}")
    
    # Create a summary plot with all metrics normalized
    plt.figure(figsize=(12, 8))
    
    # Normalize each metric to [0, 1] scale for comparison
    def normalize(values):
        if len(values) <= 1:
            return values
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return [0.5] * len(values)
        return [(v - min_val) / (max_val - min_val) for v in values]
    
    # For drawdown, lower is better, so invert the normalization
    norm_returns = normalize(total_returns)
    norm_sharpe = normalize(sharpe_ratios)
    norm_drawdown = [1 - x for x in normalize(max_drawdowns)]  # Invert so higher is better
    
    plt.plot(epochs, norm_returns, 'o-', linewidth=2, markersize=6, label='Normalized Return')
    plt.plot(epochs, norm_sharpe, 'o-', linewidth=2, markersize=6, label='Normalized Sharpe')
    plt.plot(epochs, norm_drawdown, 'o-', linewidth=2, markersize=6, label='Normalized Drawdown (inverted)')
    plt.plot(epochs, win_rates, 'o-', linewidth=2, markersize=6, label='Win Rate')
    
    plt.title('Normalized Performance Metrics')
    plt.xlabel('Training Epoch')
    plt.ylabel('Normalized Value')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Save the summary plot
    summary_path = os.path.join(save_dir, 'normalized_metrics.png')
    plt.savefig(summary_path, dpi=300, bbox_inches='tight')
    print(f"Saved normalized metrics plot to {summary_path}")
    
    plt.close('all')

def main():
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    
    # Find checkpoints
    checkpoint_files = find_checkpoints(models_dir, n_checkpoints=6)
    
    if not checkpoint_files:
        print("No checkpoints found. Please train the model first.")
        return
    
    # Evaluate checkpoints
    evaluation_results = evaluate_multiple_checkpoints(checkpoint_files, n_episodes=10, episode_length=500)
    
    if evaluation_results:
        # Plot evaluation metrics
        plot_evaluation_metrics(evaluation_results, models_dir)
    else:
        print("No evaluation results available.")

if __name__ == "__main__":
    main() 