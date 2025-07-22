"""
Policy Network for Unified Futures RL Trading System

Takes the 149-dimensional autoencoder bottleneck as input and outputs
20 position values (positive for long, negative for short) for crypto futures pairs.

Architecture:
- Input: 149-dimensional bottleneck from fusion autoencoder
- Hidden: 256 → 128 (LeakyReLU + LayerNorm + Dropout)
- Output: 20 position means (one per crypto pair)
- Action Distribution: Normal distribution with learned std devs

Features:
- Actor-Critic architecture with PPO-style training
- Entropy regularization for exploration
- Robust initialization and normalization
- Support for both long and short positions
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

from constants import (
    CRYPTO_FUTURES_PAIRS, AUTOENCODER_BOTTLENECK_DIM, TOTAL_INPUT_FEATURES,
    LEARNING_RATE_ACTOR, LEARNING_RATE_CRITIC, GAMMA, ENTROPY_WEIGHT
)

logger = logging.getLogger(__name__)

class PolicyNetwork(nn.Module):
    """
    RL policy network (Actor) that takes fusion autoencoder's bottleneck as input
    and outputs parameters for action distributions (means) for 20 crypto futures pairs.
    """
    
    def __init__(self, bottleneck_dim: int = AUTOENCODER_BOTTLENECK_DIM, 
                 n_instruments: int = 20, hidden_dims: List[int] = [256, 128]):
        super().__init__()
        self.bottleneck_dim = bottleneck_dim
        self.n_instruments = n_instruments
        
        # Create network layers with robust initialization
        layers = []
        input_dim = bottleneck_dim
        
        # Add hidden layers with robust initialization
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.LeakyReLU(0.2))
            layers.append(nn.LayerNorm(hidden_dim))
            layers.append(nn.Dropout(0.1))  # Add dropout for regularization
            input_dim = hidden_dim
            
        # Final layer for instrument position means
        self.hidden_layers = nn.Sequential(*layers)
        self.mean_head = nn.Linear(input_dim, n_instruments)
        
        # Initialize log standard deviations for action distributions
        self.log_std = nn.Parameter(torch.zeros(n_instruments))
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights using He initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='leaky_relu')
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the policy network.
        
        Args:
            x: Input state [batch_size, bottleneck_dim]
            
        Returns:
            Position means [batch_size, n_instruments]
        """
        x = self.hidden_layers(x)
        means = self.mean_head(x)
        return means
    
    def get_action_distribution(self, means: torch.Tensor) -> torch.distributions.Normal:
        """
        Get action distribution from means.
        
        Args:
            means: Position means [batch_size, n_instruments]
            
        Returns:
            Normal distribution for actions
        """
        std = torch.exp(self.log_std).expand_as(means)
        return torch.distributions.Normal(means, std)
    
    def sample_action(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Sample action from the policy.
        
        Args:
            state: Input state [batch_size, bottleneck_dim]
            
        Returns:
            actions: Sampled actions [batch_size, n_instruments]
            log_probs: Log probabilities [batch_size, n_instruments]
        """
        means = self.forward(state)
        dist = self.get_action_distribution(means)
        actions = dist.sample()
        log_probs = dist.log_prob(actions)
        return actions, log_probs

class ValueNetwork(nn.Module):
    """
    Value network (Critic) that estimates state values.
    """
    
    def __init__(self, bottleneck_dim: int = AUTOENCODER_BOTTLENECK_DIM, 
                 hidden_dims: List[int] = [256, 128]):
        super().__init__()
        self.bottleneck_dim = bottleneck_dim
        
        # Create network layers
        layers = []
        input_dim = bottleneck_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.LeakyReLU(0.2))
            layers.append(nn.LayerNorm(hidden_dim))
            input_dim = hidden_dim
        
        self.hidden_layers = nn.Sequential(*layers)
        self.value_head = nn.Linear(input_dim, 1)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights using He initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, mode='fan_in', nonlinearity='leaky_relu')
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the value network.
        
        Args:
            x: Input state [batch_size, bottleneck_dim]
            
        Returns:
            State values [batch_size, 1]
        """
        x = self.hidden_layers(x)
        values = self.value_head(x)
        return values

class UnifiedFuturesTrader:
    """
    Main RL trader that combines autoencoder, policy network, and value network.
    """
    
    def __init__(self, 
                 actor_lr: float = LEARNING_RATE_ACTOR,
                 critic_lr: float = LEARNING_RATE_CRITIC,
                 gamma: float = GAMMA,
                 entropy_weight: float = ENTROPY_WEIGHT,
                 autoencoder_path: str = None,
                 n_instruments: int = 20):
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.gamma = gamma
        self.entropy_weight = entropy_weight
        self.n_instruments = n_instruments
        
        # Initialize networks with full feature dimension (no autoencoder initially)
        self._initialize_networks(TOTAL_INPUT_FEATURES)
        
        # Initialize optimizers
        self.actor_optimizer = optim.Adam(self.policy_network.parameters(), lr=actor_lr)
        self.critic_optimizer = optim.Adam(self.value_network.parameters(), lr=critic_lr)
        
        # Add learning rate schedulers for better convergence
        self.actor_scheduler = optim.lr_scheduler.StepLR(self.actor_optimizer, step_size=50, gamma=0.9)
        self.critic_scheduler = optim.lr_scheduler.StepLR(self.critic_optimizer, step_size=50, gamma=0.9)
        
        # Load autoencoder if path provided
        if autoencoder_path and Path(autoencoder_path).exists():
            self.load_autoencoder(autoencoder_path)
        
        logger.info(f"UnifiedFuturesTrader initialized on {self.device}")
        logger.info(f"Trading {n_instruments} crypto futures pairs")
    
    def _initialize_networks(self, input_dim: int):
        """Initialize policy and value networks."""
        self.policy_network = PolicyNetwork(
            bottleneck_dim=input_dim,
            n_instruments=self.n_instruments
        ).to(self.device)
        
        self.value_network = ValueNetwork(
            bottleneck_dim=input_dim
        ).to(self.device)
        
        # Placeholder for autoencoder (will be loaded separately)
        self.autoencoder = None
    
    def load_autoencoder(self, path: str):
        """Load a trained autoencoder."""
        try:
            from autoencoder import FusionAutoencoder
            checkpoint = torch.load(path, map_location=self.device)
            
            self.autoencoder = FusionAutoencoder(
                n_features=checkpoint.get('n_features', 1242),
                bottleneck_dim=checkpoint.get('bottleneck_dim', 149)
            ).to(self.device)
            
            self.autoencoder.load_state_dict(checkpoint['model_state_dict'])
            self.autoencoder.eval()
            
            logger.info(f"Autoencoder loaded from {path}")
        except Exception as e:
            logger.warning(f"Failed to load autoencoder from {path}: {e}")
            self.autoencoder = None
    
    def encode_state(self, state: torch.Tensor) -> torch.Tensor:
        """
        Encode state using the autoencoder.
        
        Args:
            state: Raw state features [batch_size, n_features]
            
        Returns:
            Encoded state [batch_size, bottleneck_dim]
        """
        if self.autoencoder is not None:
            with torch.no_grad():
                return self.autoencoder.encode(state)
        else:
            # If no autoencoder, assume input is already encoded
            return state
    
    def get_action(self, state: torch.Tensor, training: bool = True) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get action from the policy.
        
        Args:
            state: Input state [batch_size, n_features or bottleneck_dim]
            training: Whether in training mode
            
        Returns:
            actions: Actions [batch_size, n_instruments]
            log_probs: Log probabilities [batch_size, n_instruments]
        """
        # Encode state if autoencoder is available
        encoded_state = self.encode_state(state)
        
        if training:
            actions, log_probs = self.policy_network.sample_action(encoded_state)
        else:
            # During evaluation, use mean actions
            means = self.policy_network(encoded_state)
            actions = means
            dist = self.policy_network.get_action_distribution(means)
            log_probs = dist.log_prob(actions)
        
        return actions, log_probs
    
    def get_value(self, state: torch.Tensor) -> torch.Tensor:
        """
        Get state value from the value network.
        
        Args:
            state: Input state [batch_size, n_features or bottleneck_dim]
            
        Returns:
            State values [batch_size, 1]
        """
        encoded_state = self.encode_state(state)
        return self.value_network(encoded_state)
    
    def update_policy(self, 
                     states: torch.Tensor,
                     actions: torch.Tensor,
                     rewards: torch.Tensor,
                     next_states: torch.Tensor,
                     dones: torch.Tensor) -> Dict[str, float]:
        """
        Update policy and value networks using PPO-style training.
        
        Args:
            states: Current states [batch_size, n_features]
            actions: Actions taken [batch_size, n_instruments]
            rewards: Rewards received [batch_size]
            next_states: Next states [batch_size, n_features]
            dones: Done flags [batch_size]
            
        Returns:
            Dictionary with training metrics
        """
        # Move to device
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        
        # Calculate advantages
        current_values = self.get_value(states).squeeze()
        next_values = self.get_value(next_states).squeeze()
        
        # Simple advantage calculation (can be improved with GAE)
        advantages = rewards + self.gamma * next_values * (1 - dones) - current_values
        advantages = advantages.detach()
        
        # Get current action distribution
        encoded_states = self.encode_state(states)
        means = self.policy_network(encoded_states)
        dist = self.policy_network.get_action_distribution(means)
        current_log_probs = dist.log_prob(actions).sum(dim=1)
        
        # Policy loss (negative log likelihood weighted by advantages)
        policy_loss = -(current_log_probs * advantages).mean()
        
        # Value loss (MSE)
        value_loss = F.mse_loss(current_values, rewards + self.gamma * next_values * (1 - dones))
        
        # Entropy regularization
        entropy = dist.entropy().mean()
        entropy_loss = -self.entropy_weight * entropy
        
        # Total loss
        total_loss = policy_loss + 0.5 * value_loss + entropy_loss
        
        # Update networks
        self.actor_optimizer.zero_grad()
        self.critic_optimizer.zero_grad()
        total_loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.policy_network.parameters(), 0.5)
        torch.nn.utils.clip_grad_norm_(self.value_network.parameters(), 0.5)
        
        self.actor_optimizer.step()
        self.critic_optimizer.step()
        
        # Step the learning rate schedulers
        self.actor_scheduler.step()
        self.critic_scheduler.step()
        
        return {
            'actor_loss': policy_loss.item(),
            'critic_loss': value_loss.item(),
            'entropy_loss': entropy_loss.item(),
            'total_loss': total_loss.item(),
            'entropy': entropy.item(),
            'mean_advantage': advantages.mean().item(),
            'actor_lr': self.actor_scheduler.get_last_lr()[0],
            'critic_lr': self.critic_scheduler.get_last_lr()[0]
        }
    
    def save_model(self, path: str):
        """Save the trained model."""
        torch.save({
            'policy_state_dict': self.policy_network.state_dict(),
            'value_state_dict': self.value_network.state_dict(),
            'actor_optimizer_state_dict': self.actor_optimizer.state_dict(),
            'critic_optimizer_state_dict': self.critic_optimizer.state_dict(),
            'actor_scheduler_state_dict': self.actor_scheduler.state_dict(),
            'critic_scheduler_state_dict': self.critic_scheduler.state_dict(),
            'n_instruments': self.n_instruments,
            'gamma': self.gamma,
            'entropy_weight': self.entropy_weight
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load a trained model."""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.policy_network.load_state_dict(checkpoint['policy_state_dict'])
        self.value_network.load_state_dict(checkpoint['value_state_dict'])
        self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer_state_dict'])
        self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer_state_dict'])
        
        # Load scheduler states if available
        if 'actor_scheduler_state_dict' in checkpoint:
            self.actor_scheduler.load_state_dict(checkpoint['actor_scheduler_state_dict'])
        if 'critic_scheduler_state_dict' in checkpoint:
            self.critic_scheduler.load_state_dict(checkpoint['critic_scheduler_state_dict'])
        
        logger.info(f"Model loaded from {path}")
    
    def get_position_signals(self, state: torch.Tensor) -> np.ndarray:
        """
        Get position signals for trading.
        
        Args:
            state: Input state [1, n_features]
            
        Returns:
            Position signals [n_instruments] (positive for long, negative for short)
        """
        self.policy_network.eval()
        with torch.no_grad():
            actions, _ = self.get_action(state, training=False)
            return actions.cpu().numpy().squeeze()
    
    def get_position_confidence(self, state: torch.Tensor) -> np.ndarray:
        """
        Get position confidence scores.
        
        Args:
            state: Input state [1, n_features]
            
        Returns:
            Confidence scores [n_instruments]
        """
        self.policy_network.eval()
        with torch.no_grad():
            encoded_state = self.encode_state(state)
            means = self.policy_network(encoded_state)
            # Use absolute values as confidence
            confidence = torch.abs(means).cpu().numpy().squeeze()
            return confidence 