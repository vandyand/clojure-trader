# training/trainer.py
import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import time
import os
from pathlib import Path
from dataclasses import dataclass, asdict
import json
from collections import deque
import matplotlib.pyplot as plt

from models.agent import create_agent, PPOAgent, A2CAgent
from models.reward import create_reward_function
from .environment import ForexTradingEnvironment, create_forex_environment
from config.settings import config

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Training configuration parameters"""
    # Agent configuration
    agent_type: str = "PPO"
    learning_rate: float = 1e-4
    batch_size: int = 64
    buffer_size: int = 2048
    
    # Training parameters
    total_episodes: int = 1000
    max_episode_steps: int = 1000
    update_frequency: int = 10  # Episodes between updates
    
    # PPO specific
    ppo_epochs: int = 4
    clip_epsilon: float = 0.2
    
    # Environment parameters
    initial_balance: float = 10000.0
    transaction_cost: float = 0.0001
    max_position_size: float = 0.1
    
    # Checkpointing
    save_frequency: int = 50  # Episodes between saves
    checkpoint_dir: str = "checkpoints"
    
    # Early stopping
    patience: int = 100  # Episodes without improvement
    min_improvement: float = 0.01  # Minimum improvement threshold
    
    # Logging
    log_frequency: int = 10  # Episodes between logs
    plot_frequency: int = 100  # Episodes between plots

@dataclass
class TrainingMetrics:
    """Training progress metrics"""
    episode: int = 0
    total_reward: float = 0.0
    episode_return: float = 0.0
    episode_length: int = 0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    policy_loss: float = 0.0
    value_loss: float = 0.0
    entropy: float = 0.0
    learning_rate: float = 0.0
    training_time: float = 0.0

class ForexRLTrainer:
    """
    Comprehensive RL trainer for Forex trading
    
    Features:
    - Support for PPO and A2C agents
    - Batch processing and gradient optimization
    - Checkpoint management and model saving
    - Performance tracking and visualization
    - Early stopping and hyperparameter optimization
    - TensorBoard integration
    """
    
    def __init__(self,
                 environment: ForexTradingEnvironment,
                 config: TrainingConfig = None,
                 device: str = 'auto'):
        """
        Initialize the trainer
        
        Args:
            environment: Trading environment
            config: Training configuration
            device: Device for computation
        """
        self.env = environment
        self.config = config or TrainingConfig()
        
        # Device setup
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Initialize agent with correct input dimension
        self.agent = create_agent(
            agent_type=self.config.agent_type,
            state_dim=self.env.observation_space.shape[0],  # Use environment's observation dimension
            learning_rate=self.config.learning_rate,
            batch_size=self.config.batch_size,
            buffer_size=self.config.buffer_size,
            clip_epsilon=self.config.clip_epsilon,
            ppo_epochs=self.config.ppo_epochs,
            device=self.device
        )
        
        # Training state
        self.current_episode = 0
        self.best_performance = -np.inf
        self.episodes_without_improvement = 0
        self.training_start_time = None
        
        # Metrics tracking
        self.episode_metrics = []
        self.training_history = {
            'episode_rewards': [],
            'episode_returns': [],
            'episode_lengths': [],
            'sharpe_ratios': [],
            'max_drawdowns': [],
            'policy_losses': [],
            'value_losses': [],
            'entropies': []
        }
        
        # Experience collection
        self.episode_experiences = []
        
        # Setup directories
        self.checkpoint_dir = Path(self.config.checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # TensorBoard writer (optional)
        self.writer = None
        try:
            from torch.utils.tensorboard import SummaryWriter
            self.writer = SummaryWriter(log_dir=f"runs/forex_rl_{int(time.time())}")
            logger.info("TensorBoard logging enabled")
        except ImportError:
            logger.warning("TensorBoard not available, skipping logging")
        
        logger.info(f"Initialized ForexRLTrainer: {self.config.agent_type} on {self.device}")
        logger.info(f"Training config: {self.config.total_episodes} episodes, batch_size={self.config.batch_size}")
    
    def train(self) -> Dict[str, Any]:
        """
        Main training loop
        
        Returns:
            Training results and final metrics
        """
        logger.info("Starting training...")
        self.training_start_time = time.time()
        
        try:
            for episode in range(self.config.total_episodes):
                self.current_episode = episode
                
                # Run episode
                episode_metrics = self._run_episode()
                
                # Store metrics
                self.episode_metrics.append(episode_metrics)
                self._update_training_history(episode_metrics)
                
                # Update agent if enough episodes collected
                if (episode + 1) % self.config.update_frequency == 0:
                    self._update_agent()
                
                # Logging
                if (episode + 1) % self.config.log_frequency == 0:
                    self._log_progress(episode_metrics)
                
                # Checkpointing
                if (episode + 1) % self.config.save_frequency == 0:
                    self._save_checkpoint()
                
                # Plotting
                if (episode + 1) % self.config.plot_frequency == 0:
                    self._plot_progress()
                
                # Early stopping check
                if self._check_early_stopping(episode_metrics):
                    logger.info(f"Early stopping at episode {episode + 1}")
                    break
            
            # Final save and summary
            self._save_checkpoint(final=True)
            training_summary = self._get_training_summary()
            
            logger.info("Training completed successfully!")
            return training_summary
            
        except KeyboardInterrupt:
            logger.info("Training interrupted by user")
            self._save_checkpoint(final=True)
            return self._get_training_summary()
        
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
        
        finally:
            if self.writer:
                self.writer.close()
    
    def _run_episode(self) -> TrainingMetrics:
        """Run a single training episode"""
        episode_start_time = time.time()
        
        # Reset environment
        obs = self.env.reset()
        done = False
        episode_reward = 0.0
        episode_length = 0
        episode_experiences = []
        
        while not done and episode_length < self.config.max_episode_steps:
            # Agent selects action
            obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
            action, log_prob, value = self.agent.select_action(obs_tensor)
            
            # Environment step
            next_obs, reward, done, info = self.env.step(action.squeeze(0).numpy())
            
            # Store experience
            experience = {
                'state': obs,
                'action': action.squeeze(0),
                'reward': reward,
                'next_state': next_obs,
                'done': done,
                'log_prob': log_prob.item(),
                'value': value.item()
            }
            episode_experiences.append(experience)
            
            # Update for next step
            obs = next_obs
            episode_reward += reward
            episode_length += 1
        
        # Store episode experiences
        self.episode_experiences.extend(episode_experiences)
        
        # Get episode summary from environment
        env_summary = self.env.get_episode_summary()
        
        # Create metrics
        metrics = TrainingMetrics(
            episode=self.current_episode,
            total_reward=episode_reward,
            episode_return=env_summary['total_return'],
            episode_length=episode_length,
            sharpe_ratio=env_summary['sharpe_ratio'],
            max_drawdown=env_summary['max_drawdown'],
            win_rate=env_summary['win_rate'],
            training_time=time.time() - episode_start_time
        )
        
        return metrics
    
    def _update_agent(self):
        """Update agent using collected experiences"""
        if len(self.episode_experiences) < self.config.batch_size:
            return
        
        # Prepare batch data
        batch_data = self._prepare_batch_data()
        
        # Update agent
        training_stats = self.agent.update(batch_data)
        
        # Update latest metrics with training stats
        if self.episode_metrics:
            latest_metrics = self.episode_metrics[-1]
            latest_metrics.policy_loss = training_stats.get('policy_loss', 0.0)
            latest_metrics.value_loss = training_stats.get('value_loss', 0.0)
            latest_metrics.entropy = training_stats.get('entropy', 0.0)
            latest_metrics.learning_rate = self.config.learning_rate
        
        # Clear experiences after update
        self.episode_experiences = []
        
        logger.debug(f"Agent updated: policy_loss={training_stats.get('policy_loss', 0):.4f}")
    
    def _prepare_batch_data(self) -> Dict[str, torch.Tensor]:
        """Prepare batch data for agent update"""
        # Sample experiences
        n_samples = min(len(self.episode_experiences), self.config.batch_size * 4)
        sampled_experiences = np.random.choice(
            self.episode_experiences, 
            size=n_samples, 
            replace=False
        ).tolist()
        
        # Convert to tensors
        states = torch.stack([torch.tensor(exp['state'], dtype=torch.float32) 
                             for exp in sampled_experiences])
        actions = torch.stack([exp['action'] for exp in sampled_experiences])
        rewards = torch.tensor([exp['reward'] for exp in sampled_experiences], dtype=torch.float32)
        next_states = torch.stack([torch.tensor(exp['next_state'], dtype=torch.float32) 
                                  for exp in sampled_experiences])
        dones = torch.tensor([exp['done'] for exp in sampled_experiences], dtype=torch.bool)
        log_probs = torch.tensor([exp['log_prob'] for exp in sampled_experiences], dtype=torch.float32)
        values = torch.tensor([exp['value'] for exp in sampled_experiences], dtype=torch.float32)
        
        return {
            'states': states,
            'actions': actions,
            'rewards': rewards,
            'next_states': next_states,
            'dones': dones,
            'log_probs': log_probs,
            'values': values
        }
    
    def _update_training_history(self, metrics: TrainingMetrics):
        """Update training history with episode metrics"""
        self.training_history['episode_rewards'].append(metrics.total_reward)
        self.training_history['episode_returns'].append(metrics.episode_return)
        self.training_history['episode_lengths'].append(metrics.episode_length)
        self.training_history['sharpe_ratios'].append(metrics.sharpe_ratio)
        self.training_history['max_drawdowns'].append(metrics.max_drawdown)
        self.training_history['policy_losses'].append(metrics.policy_loss)
        self.training_history['value_losses'].append(metrics.value_loss)
        self.training_history['entropies'].append(metrics.entropy)
    
    def _log_progress(self, metrics: TrainingMetrics):
        """Log training progress"""
        # Calculate running averages
        recent_episodes = min(50, len(self.training_history['episode_rewards']))
        avg_reward = np.mean(self.training_history['episode_rewards'][-recent_episodes:])
        avg_return = np.mean(self.training_history['episode_returns'][-recent_episodes:])
        avg_sharpe = np.mean(self.training_history['sharpe_ratios'][-recent_episodes:])
        
        # Console logging
        elapsed_time = time.time() - self.training_start_time
        logger.info(f"Episode {metrics.episode + 1}/{self.config.total_episodes}")
        logger.info(f"  Reward: {metrics.total_reward:.4f} (avg: {avg_reward:.4f})")
        logger.info(f"  Return: {metrics.episode_return:.4f} (avg: {avg_return:.4f})")
        logger.info(f"  Sharpe: {metrics.sharpe_ratio:.4f} (avg: {avg_sharpe:.4f})")
        logger.info(f"  Length: {metrics.episode_length}")
        logger.info(f"  Time: {elapsed_time:.1f}s")
        
        # TensorBoard logging
        if self.writer:
            self.writer.add_scalar('Episode/Reward', metrics.total_reward, metrics.episode)
            self.writer.add_scalar('Episode/Return', metrics.episode_return, metrics.episode)
            self.writer.add_scalar('Episode/Sharpe', metrics.sharpe_ratio, metrics.episode)
            self.writer.add_scalar('Episode/Length', metrics.episode_length, metrics.episode)
            self.writer.add_scalar('Episode/MaxDrawdown', metrics.max_drawdown, metrics.episode)
            self.writer.add_scalar('Training/PolicyLoss', metrics.policy_loss, metrics.episode)
            self.writer.add_scalar('Training/ValueLoss', metrics.value_loss, metrics.episode)
            self.writer.add_scalar('Training/Entropy', metrics.entropy, metrics.episode)
            
            # Running averages
            self.writer.add_scalar('Average/Reward', avg_reward, metrics.episode)
            self.writer.add_scalar('Average/Return', avg_return, metrics.episode)
            self.writer.add_scalar('Average/Sharpe', avg_sharpe, metrics.episode)
    
    def _plot_progress(self):
        """Plot training progress"""
        if len(self.training_history['episode_rewards']) < 10:
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle(f'Training Progress - Episode {self.current_episode + 1}')
        
        # Episode rewards
        axes[0, 0].plot(self.training_history['episode_rewards'])
        axes[0, 0].set_title('Episode Rewards')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Reward')
        
        # Episode returns
        axes[0, 1].plot(self.training_history['episode_returns'])
        axes[0, 1].set_title('Episode Returns')
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Return')
        
        # Sharpe ratios
        axes[0, 2].plot(self.training_history['sharpe_ratios'])
        axes[0, 2].set_title('Sharpe Ratios')
        axes[0, 2].set_xlabel('Episode')
        axes[0, 2].set_ylabel('Sharpe Ratio')
        
        # Policy losses
        axes[1, 0].plot(self.training_history['policy_losses'])
        axes[1, 0].set_title('Policy Loss')
        axes[1, 0].set_xlabel('Episode')
        axes[1, 0].set_ylabel('Loss')
        
        # Value losses
        axes[1, 1].plot(self.training_history['value_losses'])
        axes[1, 1].set_title('Value Loss')
        axes[1, 1].set_xlabel('Episode')
        axes[1, 1].set_ylabel('Loss')
        
        # Episode lengths
        axes[1, 2].plot(self.training_history['episode_lengths'])
        axes[1, 2].set_title('Episode Lengths')
        axes[1, 2].set_xlabel('Episode')
        axes[1, 2].set_ylabel('Steps')
        
        plt.tight_layout()
        
        # Save plot
        plot_path = self.checkpoint_dir / f"training_progress_ep{self.current_episode + 1}.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Training progress plot saved: {plot_path}")
    
    def _check_early_stopping(self, metrics: TrainingMetrics) -> bool:
        """Check if training should stop early"""
        # Use Sharpe ratio as performance metric
        current_performance = metrics.sharpe_ratio
        
        if current_performance > self.best_performance + self.config.min_improvement:
            self.best_performance = current_performance
            self.episodes_without_improvement = 0
            return False
        else:
            self.episodes_without_improvement += 1
            
            if self.episodes_without_improvement >= self.config.patience:
                logger.info(f"No improvement for {self.config.patience} episodes")
                return True
        
        return False
    
    def _save_checkpoint(self, final: bool = False):
        """Save training checkpoint"""
        checkpoint_name = "final_checkpoint.pt" if final else f"checkpoint_ep{self.current_episode + 1}.pt"
        checkpoint_path = self.checkpoint_dir / checkpoint_name
        
        # Save agent
        self.agent.save_checkpoint(checkpoint_path)
        
        # Save training state
        training_state = {
            'episode': self.current_episode,
            'best_performance': self.best_performance,
            'episodes_without_improvement': self.episodes_without_improvement,
            'training_history': self.training_history,
            'config': asdict(self.config)
        }
        
        state_path = self.checkpoint_dir / f"training_state_{checkpoint_name}"
        torch.save(training_state, state_path)
        
        # Save metrics as JSON
        metrics_path = self.checkpoint_dir / f"metrics_{checkpoint_name.replace('.pt', '.json')}"
        with open(metrics_path, 'w') as f:
            json.dump([asdict(m) for m in self.episode_metrics], f, indent=2)
        
        logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    def _get_training_summary(self) -> Dict[str, Any]:
        """Get comprehensive training summary"""
        if not self.episode_metrics:
            return {}
        
        # Calculate final statistics
        final_metrics = self.episode_metrics[-1]
        total_time = time.time() - self.training_start_time if self.training_start_time else 0
        
        # Performance statistics
        rewards = self.training_history['episode_rewards']
        returns = self.training_history['episode_returns']
        sharpe_ratios = self.training_history['sharpe_ratios']
        
        summary = {
            'training_completed': True,
            'total_episodes': len(self.episode_metrics),
            'total_time': total_time,
            'final_performance': {
                'reward': final_metrics.total_reward,
                'return': final_metrics.episode_return,
                'sharpe_ratio': final_metrics.sharpe_ratio,
                'max_drawdown': final_metrics.max_drawdown
            },
            'best_performance': {
                'best_reward': max(rewards) if rewards else 0,
                'best_return': max(returns) if returns else 0,
                'best_sharpe': max(sharpe_ratios) if sharpe_ratios else 0
            },
            'average_performance': {
                'avg_reward': np.mean(rewards) if rewards else 0,
                'avg_return': np.mean(returns) if returns else 0,
                'avg_sharpe': np.mean(sharpe_ratios) if sharpe_ratios else 0
            },
            'config': asdict(self.config),
            'checkpoint_dir': str(self.checkpoint_dir)
        }
        
        return summary
    
    def load_checkpoint(self, checkpoint_path: str):
        """Load training checkpoint"""
        # Load agent
        self.agent.load_checkpoint(checkpoint_path)
        
        # Load training state
        state_path = checkpoint_path.replace('.pt', '_training_state.pt')
        if os.path.exists(state_path):
            training_state = torch.load(state_path, map_location=self.device)
            self.current_episode = training_state['episode']
            self.best_performance = training_state['best_performance']
            self.episodes_without_improvement = training_state['episodes_without_improvement']
            self.training_history = training_state['training_history']
            
            logger.info(f"Training state loaded from {state_path}")
        
        logger.info(f"Checkpoint loaded: {checkpoint_path}")


def create_trainer(data: pd.DataFrame, config: TrainingConfig = None, **kwargs) -> ForexRLTrainer:
    """
    Factory function to create Forex RL trainer
    
    Args:
        data: Historical price data
        config: Training configuration
        **kwargs: Additional configuration
        
    Returns:
        Configured ForexRLTrainer
    """
    # Create environment
    env_config = {
        'initial_balance': config.initial_balance if config else 10000.0,
        'transaction_cost': config.transaction_cost if config else 0.0001,
        'max_position_size': config.max_position_size if config else 0.1,
        'max_episode_steps': config.max_episode_steps if config else 1000,
        **kwargs
    }
    
    env = create_forex_environment(data=data, **env_config)
    
    # Create trainer
    return ForexRLTrainer(environment=env, config=config)


def test_trainer():
    """Test the trainer implementation"""
    logger.info("Testing Forex RL trainer...")
    
    # Create synthetic data
    np.random.seed(42)
    n_steps = 1000
    
    # Generate price data
    initial_price = 1.0
    returns = np.random.normal(0, 0.01, n_steps)
    prices = [initial_price]
    
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'open': prices[:-1],
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices[:-1]],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices[:-1]],
        'close': prices[1:],
        'volume': np.random.randint(1000, 10000, n_steps)
    })
    
    # Create training config
    config = TrainingConfig(
        total_episodes=20,
        max_episode_steps=50,
        update_frequency=5,
        log_frequency=5,
        save_frequency=10,
        plot_frequency=20
    )
    
    # Create trainer
    trainer = create_trainer(data=data, config=config)
    
    # Run short training
    results = trainer.train()
    
    logger.info("✓ Trainer test completed:")
    logger.info(f"  Episodes: {results['total_episodes']}")
    logger.info(f"  Final Sharpe: {results['final_performance']['sharpe_ratio']:.4f}")
    logger.info(f"  Best Sharpe: {results['best_performance']['best_sharpe']:.4f}")
    logger.info(f"  Training time: {results['total_time']:.1f}s")
    
    return True


if __name__ == "__main__":
    # Run tests
    test_trainer() 