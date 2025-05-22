#!/usr/bin/env python
"""
Advanced plotting script for RLTrader training progress with multiple metrics and improved visualization.
"""
import os
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt
import glob
from pathlib import Path
import re
import seaborn as sns

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_epoch_number(checkpoint_path):
    """Extract epoch number from checkpoint path."""
    match = re.search(r'epoch_(\d+)\.pt', checkpoint_path)
    if match:
        return int(match.group(1))
    return 0

def load_metrics_from_checkpoint(checkpoint_path, device="cpu"):
    """Load metrics from checkpoint."""
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        return checkpoint['metrics']
    except Exception as e:
        print(f"Error loading checkpoint {checkpoint_path}: {e}")
        return None

def collect_all_metrics(models_dir="models"):
    """Collect metrics from all checkpoints."""
    # Find all checkpoint files
    checkpoint_pattern = os.path.join(models_dir, "checkpoint_epoch_*.pt")
    checkpoint_files = glob.glob(checkpoint_pattern)
    
    if not checkpoint_files:
        print(f"No checkpoint files found matching pattern: {checkpoint_pattern}")
        return None
    
    # Sort by epoch number
    checkpoint_files = sorted(checkpoint_files, key=extract_epoch_number)
    
    # Load metrics from each checkpoint
    all_metrics = {}
    epochs = []
    
    for checkpoint_file in checkpoint_files:
        epoch = extract_epoch_number(checkpoint_file)
        metrics = load_metrics_from_checkpoint(checkpoint_file)
        
        if metrics:
            epochs.append(epoch)
            for key, value in metrics.items():
                if key not in all_metrics:
                    all_metrics[key] = []
                all_metrics[key].append(value)
    
    return epochs, all_metrics

def plot_training_metrics(epochs, metrics, save_dir="models"):
    """
    Create detailed plots for all training metrics.
    """
    if not metrics:
        print("No metrics data to plot.")
        return
    
    # Set up plot style
    sns.set(style="darkgrid", font_scale=1.2)
    plt.rcParams['figure.figsize'] = [12, 10]
    
    # Create a figure with multiple subplots
    n_metrics = len(metrics)
    n_rows = (n_metrics + 1) // 2  # Calculate rows needed for 2 plots per row
    
    fig, axes = plt.subplots(n_rows, 2, figsize=(15, 4 * n_rows))
    if n_rows == 1:
        axes = np.array([axes])  # Ensure axes is 2D array
    fig.suptitle('RLTrader Training Progress', fontsize=16)
    
    # Flatten axes for easier indexing
    axes = axes.flatten()
    
    # Plot each metric
    for i, (metric_name, metric_values) in enumerate(metrics.items()):
        if i < len(axes):
            ax = axes[i]
            
            if isinstance(metric_values[0], list):
                # For list values (like actor_loss, critic_loss), use last value in each epoch
                values_to_plot = [values[-1] if values else 0 for values in metric_values]
            else:
                values_to_plot = metric_values
            
            # Plot the metric
            ax.plot(epochs, values_to_plot, 'o-', linewidth=2, markersize=4)
            
            # Format the plot
            ax.set_title(f'{metric_name.replace("_", " ").title()}')
            ax.set_xlabel('Epoch')
            ax.set_ylabel('Value')
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # For loss metrics, use log scale if values are mostly negative
            if 'loss' in metric_name.lower() and any(v < 0 for v in values_to_plot if v is not None):
                # For negative values, plot abs values with log scale
                abs_values = [abs(v) if v is not None else None for v in values_to_plot]
                ax.clear()
                ax.plot(epochs, abs_values, 'o-', linewidth=2, markersize=4)
                ax.set_yscale('log')
                ax.set_title(f'{metric_name.replace("_", " ").title()} (log scale, absolute values)')
                ax.set_xlabel('Epoch')
                ax.set_ylabel('Absolute Value')
    
    # Hide any unused subplots
    for i in range(len(metrics), len(axes)):
        axes[i].set_visible(False)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust to make room for suptitle
    
    # Save the plot
    save_path = os.path.join(save_dir, 'training_metrics.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved training metrics plot to {save_path}")
    
    # Create a separate plot for each group of related metrics
    
    # Plot loss metrics
    loss_metrics = {k: v for k, v in metrics.items() if 'loss' in k.lower()}
    if loss_metrics:
        plt.figure(figsize=(10, 6))
        for metric_name, metric_values in loss_metrics.items():
            if isinstance(metric_values[0], list):
                values = [abs(values[-1]) if values and values[-1] is not None else 0 for values in metric_values]
            else:
                values = [abs(v) if v is not None else 0 for v in metric_values]
            plt.plot(epochs, values, 'o-', linewidth=2, markersize=4, label=metric_name.replace('_', ' ').title())
        
        plt.title('Training Losses (Absolute Values)')
        plt.xlabel('Epoch')
        plt.ylabel('Loss (log scale)')
        plt.yscale('log')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Save loss plot
        loss_plot_path = os.path.join(save_dir, 'training_losses.png')
        plt.savefig(loss_plot_path, dpi=300, bbox_inches='tight')
        print(f"Saved training losses plot to {loss_plot_path}")
    
    # Plot reward metrics
    reward_metrics = {k: v for k, v in metrics.items() if any(term in k.lower() for term in ['reward', 'return', 'sharpe'])}
    if reward_metrics:
        plt.figure(figsize=(10, 6))
        for metric_name, metric_values in reward_metrics.items():
            if isinstance(metric_values[0], list):
                values = [values[-1] if values and values[-1] is not None else 0 for values in metric_values]
            else:
                values = [v if v is not None else 0 for v in metric_values]
            plt.plot(epochs, values, 'o-', linewidth=2, markersize=4, label=metric_name.replace('_', ' ').title())
        
        plt.title('Reward Metrics')
        plt.xlabel('Epoch')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Save reward plot
        reward_plot_path = os.path.join(save_dir, 'reward_metrics.png')
        plt.savefig(reward_plot_path, dpi=300, bbox_inches='tight')
        print(f"Saved reward metrics plot to {reward_plot_path}")
    
    plt.close('all')

def main():
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    epochs, metrics = collect_all_metrics(models_dir)
    
    if epochs and metrics:
        plot_training_metrics(epochs, metrics, models_dir)
    else:
        print("No metrics data available. Make sure you have trained the model and checkpoints exist.")

if __name__ == "__main__":
    main() 