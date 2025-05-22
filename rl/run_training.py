import os
import sys
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from rl.policy_network import RLTrader
from rl.train_rl import train_policy, evaluate_policy
import torch
import numpy as np

def main():
    """Run a short training session as a test"""
    print("Starting RL training test...")
    
    # Create RL trader
    trader = RLTrader(actor_lr=1e-4, critic_lr=1e-3, gamma=0.99, entropy_weight=0.01)
    
    # Train for a few epochs
    trader = train_policy(trader, batch_size=32, n_epochs=3, save_interval=1)
    
    # Evaluate
    eval_results = evaluate_policy(trader, n_days=50)
    
    print(f"Training test completed. Total return: {eval_results['total_return']:.4f}")

if __name__ == "__main__":
    main() 