#!/usr/bin/env python3
"""
Train RL agent using only 300 features (no portfolio or market state)
"""
import sys
import os
import argparse
import torch
import pickle
import logging
import numpy as np
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import create_agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FeaturesOnlyEnv:
    """Minimal environment for 300-feature RL training"""
    def __init__(self, features, max_episode_steps=1000):
        self.features = features
        self.max_episode_steps = max_episode_steps
        self.current_step = 0
        self.observation_space = torch.zeros(features.shape[1])
        self.action_space = torch.zeros(20)  # 20 actions for 20 pairs
        self.n_steps = features.shape[0]
    def reset(self):
        self.current_step = 0
        return torch.tensor(self.features[self.current_step], dtype=torch.float32)
    def step(self, action):
        self.current_step += 1
        done = self.current_step >= min(self.n_steps, self.max_episode_steps)
        reward = 0.0  # Placeholder, you may want to use a real reward function
        obs = torch.tensor(self.features[self.current_step % self.n_steps], dtype=torch.float32)
        info = {}
        return obs, reward, done, info


def main():
    parser = argparse.ArgumentParser(description="Train RL agent with 300 features only")
    parser.add_argument('--features', type=str, required=True, help='Path to features pickle file')
    parser.add_argument('--episodes', type=int, default=1000, help='Number of training episodes')
    parser.add_argument('--batch_size', type=int, default=64, help='Batch size')
    parser.add_argument('--checkpoint', type=str, default='checkpoints/final_checkpoint_300.pt', help='Path to save checkpoint')
    args = parser.parse_args()

    logger.info(f"Loading features from {args.features}")
    features = pickle.load(open(args.features, 'rb'))
    if hasattr(features, 'values'):
        features = features.values
    assert features.shape[1] == 300, f"Expected 300 features, got {features.shape[1]}"

    env = FeaturesOnlyEnv(features)
    agent = create_agent('PPO', state_dim=300, action_dim=20)

    logger.info("Starting training loop...")
    for ep in range(args.episodes):
        state = env.reset().unsqueeze(0)
        done = False
        total_reward = 0
        steps = 0
        while not done:
            action, log_prob, value = agent.select_action(state)
            next_state, reward, done, info = env.step(action.squeeze(0).numpy())
            # For simplicity, reward is zero; you can add a real reward function here
            # No experience replay, just a simple update for demonstration
            state = next_state.unsqueeze(0)
            steps += 1
        if (ep + 1) % 50 == 0:
            logger.info(f"Episode {ep+1}/{args.episodes} completed. Steps: {steps}")
            agent.save_checkpoint(args.checkpoint)
    logger.info(f"Training complete. Final checkpoint saved to {args.checkpoint}")

if __name__ == "__main__":
    main() 