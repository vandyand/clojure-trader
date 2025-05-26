#!/usr/bin/env python3
"""
Dedicated inference script for Forex RL agent
"""
import sys
import os
import argparse
import torch
import pickle
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import create_agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run inference with trained RL agent.")
    parser.add_argument('--features', type=str, required=False, default='data/features_20250525_221711.pkl', help='Path to features pickle file')
    parser.add_argument('--checkpoint', type=str, required=False, default='checkpoints/final_checkpoint.pt', help='Path to agent checkpoint')
    parser.add_argument('--deterministic', action='store_true', help='Use deterministic policy (no sampling)')
    args = parser.parse_args()

    # Load features
    logger.info(f"Loading features from {args.features}")
    features = pickle.load(open(args.features, 'rb'))
    latest_features = features.iloc[-1].values  # Get the latest feature vector
    state = torch.tensor(latest_features, dtype=torch.float32).unsqueeze(0)  # Shape: [1, 300]

    # Load agent
    logger.info(f"Loading agent from {args.checkpoint}")
    agent = create_agent('PPO')
    agent.load_checkpoint(args.checkpoint)

    # Run inference
    logger.info("Running inference...")
    action, log_prob, value = agent.select_action(state, deterministic=args.deterministic)
    print("Action:", action.cpu().numpy())
    print("Log prob:", log_prob.cpu().numpy())
    print("Value:", value.cpu().numpy())

if __name__ == "__main__":
    main() 