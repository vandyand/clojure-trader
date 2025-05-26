#!/usr/bin/env python3
"""
Script to train the Forex RL agent and run inference
"""
import sys
import os
import argparse
import torch
import pickle
import logging
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import create_agent
from training.trainer import ForexRLTrainer, TrainingConfig
from training.environment import create_forex_environment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data(file_path: str) -> pd.DataFrame:
    """Load data from either CSV or pickle file"""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.pkl'):
        return pd.read_pickle(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

def train_model(args):
    """Train the RL agent"""
    logger.info("Loading training data...")
    data = load_data(args.data_path)
    
    if isinstance(data, dict):
        logger.info(f"Loaded dict with keys: {list(data.keys())}")
        env_data = data
    else:
        logger.info(f"Loaded DataFrame with shape: {data.shape}")
        env_data = data
    
    logger.info("Initializing training environment...")
    env = create_forex_environment(
        data=env_data,
        lookback_window=args.lookback_window,
        max_episode_steps=args.max_episode_steps
    )
    
    # Create training config
    config = TrainingConfig(
        agent_type=args.agent_type,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        total_episodes=args.episodes,
        max_episode_steps=args.max_episode_steps,
        save_frequency=args.save_frequency
    )
    
    # Initialize trainer
    trainer = ForexRLTrainer(environment=env, config=config)
    
    # Train model
    logger.info("Starting training...")
    training_summary = trainer.train()
    
    # Save final checkpoint
    checkpoint_path = Path(args.checkpoint_dir) / "final_checkpoint.pt"
    trainer.agent.save_checkpoint(str(checkpoint_path))
    logger.info(f"Training completed. Final checkpoint saved to {checkpoint_path}")
    
    return checkpoint_path

def run_inference(args):
    """Run inference with trained model"""
    logger.info(f"Loading features from {args.features}")
    features = pickle.load(open(args.features, 'rb'))
    latest_features = features.iloc[-1].values
    state = torch.tensor(latest_features, dtype=torch.float32).unsqueeze(0)
    
    logger.info(f"Loading agent from {args.checkpoint}")
    agent = create_agent('PPO')
    agent.load_checkpoint(args.checkpoint)
    
    logger.info("Running inference...")
    action, log_prob, value = agent.select_action(state, deterministic=args.deterministic)
    print("\nInference Results:")
    print("Action:", action.cpu().numpy())
    print("Log probability:", log_prob.cpu().numpy())
    print("Value estimate:", value.cpu().numpy())

def main():
    parser = argparse.ArgumentParser(description="Train Forex RL agent and run inference")
    
    # Training arguments
    parser.add_argument('--train', action='store_true', help='Run training')
    parser.add_argument('--data_path', type=str, default='data/forex_data.csv', help='Path to training data')
    parser.add_argument('--agent_type', type=str, default='PPO', help='RL agent type (PPO or A2C)')
    parser.add_argument('--learning_rate', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--batch_size', type=int, default=64, help='Batch size')
    parser.add_argument('--episodes', type=int, default=1000, help='Number of training episodes')
    parser.add_argument('--max_episode_steps', type=int, default=1000, help='Maximum steps per episode')
    parser.add_argument('--lookback_window', type=int, default=20, help='Lookback window for features')
    parser.add_argument('--save_frequency', type=int, default=50, help='Save checkpoint every N episodes')
    parser.add_argument('--checkpoint_dir', type=str, default='checkpoints', help='Directory to save checkpoints')
    
    # Inference arguments
    parser.add_argument('--infer', action='store_true', help='Run inference')
    parser.add_argument('--features', type=str, default='data/features.pkl', help='Path to features pickle file')
    parser.add_argument('--checkpoint', type=str, default='checkpoints/final_checkpoint.pt', help='Path to agent checkpoint')
    parser.add_argument('--deterministic', action='store_true', help='Use deterministic policy (no sampling)')
    
    args = parser.parse_args()
    
    # Create checkpoint directory if it doesn't exist
    if args.train:
        os.makedirs(args.checkpoint_dir, exist_ok=True)
    
    # Run training if requested
    if args.train:
        checkpoint_path = train_model(args)
        if args.infer:
            args.checkpoint = str(checkpoint_path)
    
    # Run inference if requested
    if args.infer:
        run_inference(args)

if __name__ == "__main__":
    main() 