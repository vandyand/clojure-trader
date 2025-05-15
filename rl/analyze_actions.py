#!/usr/bin/env python
"""
Analyze the raw action values from the RL trading model.
"""
import torch
import numpy as np
import matplotlib.pyplot as plt
from rl.trading_system import TradingSystem
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA

def main():
    # Create trading system
    system = TradingSystem()
    
    # Load market data
    print("Loading market data...")
    market_data = system._load_market_data()
    features = market_data['features']
    price_changes = market_data['price_changes']
    
    # Generate actions
    print("Generating actions...")
    raw_actions = []
    normalized_actions = []
    
    sample_size = min(100, len(features))
    
    for i in range(sample_size):
        state = features[i]
        # Get raw action
        action, _ = system.trader.get_action(torch.tensor(state, dtype=torch.float32), training=False)
        raw_action = action.detach().numpy()
        raw_actions.append(raw_action)
        
        # Get normalized action
        normalized_action = system.reward_calculator.normalize_positions(raw_action)
        normalized_actions.append(normalized_action)
    
    # Convert to arrays
    raw_actions_array = np.array(raw_actions)
    normalized_actions_array = np.array(normalized_actions)
    
    # Print stats
    print("\nRaw Action Statistics:")
    print(f"Min: {np.min(raw_actions_array):.4f}")
    print(f"Max: {np.max(raw_actions_array):.4f}")
    print(f"Mean: {np.mean(raw_actions_array):.4f}")
    print(f"Median: {np.median(raw_actions_array):.4f}")
    print(f"Std Dev: {np.std(raw_actions_array):.4f}")
    print(f"% Positive: {np.mean(raw_actions_array > 0) * 100:.2f}%")
    print(f"% Negative: {np.mean(raw_actions_array < 0) * 100:.2f}%")
    
    print("\nNormalized Action Statistics:")
    print(f"Min: {np.min(normalized_actions_array):.4f}")
    print(f"Max: {np.max(normalized_actions_array):.4f}")
    print(f"Mean: {np.mean(normalized_actions_array):.4f}")
    print(f"Median: {np.median(normalized_actions_array):.4f}")
    print(f"Std Dev: {np.std(normalized_actions_array):.4f}")
    print(f"% Positive: {np.mean(normalized_actions_array > 0) * 100:.2f}%")
    print(f"% Negative: {np.mean(normalized_actions_array < 0) * 100:.2f}%")
    
    # Plot histograms
    plt.figure(figsize=(15, 10))
    
    # Raw actions histogram
    plt.subplot(2, 2, 1)
    plt.hist(raw_actions_array.flatten(), bins=50)
    plt.title('Raw Action Distribution')
    plt.xlabel('Action Value')
    plt.ylabel('Frequency')
    plt.axvline(x=0, color='r', linestyle='--')
    
    # Normalized actions histogram
    plt.subplot(2, 2, 2)
    plt.hist(normalized_actions_array.flatten(), bins=50)
    plt.title('Normalized Action Distribution')
    plt.xlabel('Action Value')
    plt.ylabel('Frequency')
    plt.axvline(x=0, color='r', linestyle='--')
    
    # Plot mean action by instrument
    plt.subplot(2, 2, 3)
    instrument_means = np.mean(raw_actions_array, axis=0)
    plt.bar(range(len(instrument_means)), instrument_means)
    plt.title('Mean Raw Action by Instrument')
    plt.xlabel('Instrument Index')
    plt.ylabel('Mean Action')
    plt.axhline(y=0, color='r', linestyle='--')
    
    # Plot mean normalized action by instrument
    plt.subplot(2, 2, 4)
    normalized_means = np.mean(normalized_actions_array, axis=0)
    plt.bar(range(len(normalized_means)), normalized_means)
    plt.title('Mean Normalized Action by Instrument')
    plt.xlabel('Instrument Index')
    plt.ylabel('Mean Action')
    plt.axhline(y=0, color='r', linestyle='--')
    
    plt.tight_layout()
    plt.savefig('action_analysis.png')
    print("Saved plots to action_analysis.png")

if __name__ == "__main__":
    main() 