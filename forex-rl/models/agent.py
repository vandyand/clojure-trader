# models/agent.py
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from collections import deque
import random

from .network import PolicyNetwork, ValueNetwork, CombinedNetwork
from .reward import ForexRewardFunction
from config.settings import config

logger = logging.getLogger(__name__)

class ExperienceBuffer:
    """
    Experience replay buffer for storing and sampling experiences
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Initialize experience buffer
        
        Args:
            capacity: Maximum number of experiences to store
        """
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.position = 0
        
    def push(self, state: torch.Tensor, action: torch.Tensor, reward: float, 
             next_state: torch.Tensor, done: bool, log_prob: float = None, value: float = None):
        """Add experience to buffer"""
        experience = {
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done,
            'log_prob': log_prob,
            'value': value
        }
        
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
            self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size: int) -> Dict[str, torch.Tensor]:
        """Sample batch of experiences"""
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
        # Stack experiences
        states = torch.stack([exp['state'] for exp in batch])
        actions = torch.stack([exp['action'] for exp in batch])
        rewards = torch.tensor([exp['reward'] for exp in batch], dtype=torch.float32)
        next_states = torch.stack([exp['next_state'] for exp in batch])
        dones = torch.tensor([exp['done'] for exp in batch], dtype=torch.bool)
        
        result = {
            'states': states,
            'actions': actions,
            'rewards': rewards,
            'next_states': next_states,
            'dones': dones
        }
        
        # Add optional fields if available
        if batch[0]['log_prob'] is not None:
            result['log_probs'] = torch.tensor([exp['log_prob'] for exp in batch], dtype=torch.float32)
        if batch[0]['value'] is not None:
            result['values'] = torch.tensor([exp['value'] for exp in batch], dtype=torch.float32)
        
        return result
    
    def get_all(self) -> Dict[str, torch.Tensor]:
        """Get all experiences in buffer"""
        if len(self.buffer) == 0:
            return {}
        
        return self.sample(len(self.buffer))
    
    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()
        self.position = 0
    
    def __len__(self):
        return len(self.buffer)


class BaseAgent:
    """
    Base class for RL agents
    """
    
    def __init__(self,
                 state_dim: int = 300,
                 action_dim: int = 20,
                 learning_rate: float = 1e-4,
                 device: str = 'auto'):
        """
        Initialize base agent
        
        Args:
            state_dim: State space dimension
            action_dim: Action space dimension
            learning_rate: Learning rate for optimization
            device: Device for computation
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        
        # Device setup
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Initialize networks (to be implemented by subclasses)
        self.policy_net = None
        self.value_net = None
        self.optimizer = None
        
        # Training statistics
        self.training_stats = {
            'episodes': 0,
            'total_reward': 0.0,
            'policy_loss': 0.0,
            'value_loss': 0.0,
            'entropy': 0.0
        }
        
        logger.info(f"Initialized {self.__class__.__name__} on device: {self.device}")
    
    def select_action(self, state: torch.Tensor, deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Select action given state
        
        Args:
            state: Current state
            deterministic: Whether to select deterministic action
            
        Returns:
            action: Selected action
            log_prob: Log probability of action
        """
        raise NotImplementedError
    
    def update(self, experiences: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        Update agent parameters
        
        Args:
            experiences: Batch of experiences
            
        Returns:
            Training statistics
        """
        raise NotImplementedError
    
    def save_checkpoint(self, filepath: str):
        """Save agent checkpoint"""
        checkpoint = {
            'policy_state_dict': self.policy_net.state_dict() if self.policy_net else None,
            'value_state_dict': self.value_net.state_dict() if self.value_net else None,
            'combined_state_dict': getattr(self, 'combined_net', None) and self.combined_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict() if self.optimizer else None,
            'training_stats': self.training_stats,
            'config': {
                'state_dim': self.state_dim,
                'action_dim': self.action_dim,
                'learning_rate': self.learning_rate,
                'use_combined_network': getattr(self, 'use_combined_network', False)
            }
        }
        
        torch.save(checkpoint, filepath)
        logger.info(f"Agent checkpoint saved to {filepath}")
    
    def load_checkpoint(self, filepath: str):
        """Load agent checkpoint"""
        checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
        
        if hasattr(self, 'combined_net') and self.combined_net and checkpoint['combined_state_dict']:
            self.combined_net.load_state_dict(checkpoint['combined_state_dict'])
        else:
            if self.policy_net and checkpoint['policy_state_dict']:
                self.policy_net.load_state_dict(checkpoint['policy_state_dict'])
            if self.value_net and checkpoint['value_state_dict']:
                self.value_net.load_state_dict(checkpoint['value_state_dict'])
        
        if self.optimizer and checkpoint['optimizer_state_dict']:
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        self.training_stats = checkpoint.get('training_stats', self.training_stats)
        
        logger.info(f"Agent checkpoint loaded from {filepath}")


class PPOAgent(BaseAgent):
    """
    Proximal Policy Optimization (PPO) Agent
    """
    
    def __init__(self,
                 state_dim: int = 300,
                 action_dim: int = 20,
                 learning_rate: float = 1e-4,
                 clip_epsilon: float = 0.2,
                 ppo_epochs: int = 4,
                 value_loss_coef: float = 0.5,
                 entropy_coef: float = 0.01,
                 max_grad_norm: float = 0.5,
                 use_combined_network: bool = True,
                 **kwargs):
        """
        Initialize PPO agent
        
        Args:
            clip_epsilon: PPO clipping parameter
            ppo_epochs: Number of PPO update epochs
            value_loss_coef: Value loss coefficient
            entropy_coef: Entropy loss coefficient
            max_grad_norm: Maximum gradient norm for clipping
            use_combined_network: Whether to use combined policy-value network
        """
        super().__init__(state_dim, action_dim, learning_rate, kwargs.get('device', 'auto'))
        
        self.clip_epsilon = clip_epsilon
        self.ppo_epochs = ppo_epochs
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.use_combined_network = use_combined_network
        
        # Initialize networks
        if use_combined_network:
            self.combined_net = CombinedNetwork(
                input_dim=state_dim,
                output_dim=action_dim,
                action_type='continuous',
                device=self.device
            )
            self.optimizer = optim.Adam(self.combined_net.parameters(), lr=learning_rate)
        else:
            self.policy_net = PolicyNetwork(
                input_dim=state_dim,
                output_dim=action_dim,
                action_type='continuous',
                device=self.device
            )
            self.value_net = ValueNetwork(
                input_dim=state_dim,
                device=self.device
            )
            
            # Combined optimizer
            params = list(self.policy_net.parameters()) + list(self.value_net.parameters())
            self.optimizer = optim.Adam(params, lr=learning_rate)
        
        # Experience buffer
        self.buffer = ExperienceBuffer(capacity=kwargs.get('buffer_size', 2048))
        
        logger.info(f"Initialized PPO agent: clip_eps={clip_epsilon}, epochs={ppo_epochs}, combined_net={use_combined_network}")
    
    def select_action(self, state: torch.Tensor, deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Select action using policy network
        
        Returns:
            action: Selected action
            log_prob: Log probability of action
            value: State value estimate
        """
        # Set to eval mode for inference
        if self.use_combined_network:
            self.combined_net.eval()
        else:
            self.policy_net.eval()
            self.value_net.eval()
        
        with torch.no_grad():
            if self.use_combined_network:
                policy_output, value, _ = self.combined_net(state)
                action_mean, action_std = policy_output
            else:
                action_mean, action_std = self.policy_net(state)
                value = self.value_net(state)
            
            if deterministic:
                action = action_mean
                # Calculate log prob for deterministic action
                dist = torch.distributions.Normal(action_mean, action_std)
                log_prob = dist.log_prob(action).sum(dim=-1)
            else:
                # Sample from policy distribution
                dist = torch.distributions.Normal(action_mean, action_std)
                action = dist.sample()
                log_prob = dist.log_prob(action).sum(dim=-1)
        
        return action, log_prob, value
    
    def compute_gae(self, rewards: torch.Tensor, values: torch.Tensor, 
                    next_values: torch.Tensor, dones: torch.Tensor,
                    gamma: float = 0.99, gae_lambda: float = 0.95) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute Generalized Advantage Estimation (GAE)
        
        Returns:
            advantages: Computed advantages
            returns: Computed returns
        """
        advantages = torch.zeros_like(rewards)
        returns = torch.zeros_like(rewards)
        
        gae = 0
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = next_values[t] if not dones[t] else 0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + gamma * next_value * (1 - dones[t].float()) - values[t]
            gae = delta + gamma * gae_lambda * (1 - dones[t].float()) * gae
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]
        
        return advantages, returns
    
    def update(self, experiences: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        Update PPO agent using collected experiences
        """
        # Set to training mode
        if self.use_combined_network:
            self.combined_net.train()
        else:
            self.policy_net.train()
            self.value_net.train()
        
        states = experiences['states'].to(self.device)
        actions = experiences['actions'].to(self.device)
        old_log_probs = experiences['log_probs'].to(self.device)
        rewards = experiences['rewards'].to(self.device)
        values = experiences['values'].to(self.device)
        dones = experiences['dones'].to(self.device)
        
        # Compute advantages and returns
        with torch.no_grad():
            if self.use_combined_network:
                _, next_values, _ = self.combined_net(states)
            else:
                next_values = self.value_net(states)
            
            advantages, returns = self.compute_gae(rewards, values, next_values, dones)
            
            # Normalize advantages
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # PPO update loop
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        
        for epoch in range(self.ppo_epochs):
            # Forward pass
            if self.use_combined_network:
                policy_output, current_values, _ = self.combined_net(states)
                action_mean, action_std = policy_output
            else:
                action_mean, action_std = self.policy_net(states)
                current_values = self.value_net(states)
            
            # Calculate current log probabilities
            dist = torch.distributions.Normal(action_mean, action_std)
            current_log_probs = dist.log_prob(actions).sum(dim=-1)
            entropy = dist.entropy().sum(dim=-1).mean()
            
            # PPO policy loss
            ratio = torch.exp(current_log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            value_loss = F.mse_loss(current_values, returns)
            
            # Total loss
            total_loss = policy_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy
            
            # Backward pass
            self.optimizer.zero_grad()
            total_loss.backward()
            
            # Gradient clipping
            if self.use_combined_network:
                torch.nn.utils.clip_grad_norm_(self.combined_net.parameters(), self.max_grad_norm)
            else:
                torch.nn.utils.clip_grad_norm_(
                    list(self.policy_net.parameters()) + list(self.value_net.parameters()),
                    self.max_grad_norm
                )
            
            self.optimizer.step()
            
            # Accumulate losses
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy += entropy.item()
        
        # Update training statistics
        self.training_stats['episodes'] += 1
        self.training_stats['policy_loss'] = total_policy_loss / self.ppo_epochs
        self.training_stats['value_loss'] = total_value_loss / self.ppo_epochs
        self.training_stats['entropy'] = total_entropy / self.ppo_epochs
        
        return {
            'policy_loss': self.training_stats['policy_loss'],
            'value_loss': self.training_stats['value_loss'],
            'entropy': self.training_stats['entropy'],
            'total_loss': self.training_stats['policy_loss'] + self.training_stats['value_loss']
        }


class A2CAgent(BaseAgent):
    """
    Advantage Actor-Critic (A2C) Agent
    """
    
    def __init__(self,
                 state_dim: int = 300,
                 action_dim: int = 20,
                 learning_rate: float = 1e-4,
                 value_loss_coef: float = 0.5,
                 entropy_coef: float = 0.01,
                 max_grad_norm: float = 0.5,
                 use_combined_network: bool = True,
                 **kwargs):
        """
        Initialize A2C agent
        """
        super().__init__(state_dim, action_dim, learning_rate, kwargs.get('device', 'auto'))
        
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.use_combined_network = use_combined_network
        
        # Initialize networks
        if use_combined_network:
            self.combined_net = CombinedNetwork(
                input_dim=state_dim,
                output_dim=action_dim,
                action_type='continuous',
                device=self.device
            )
            self.optimizer = optim.Adam(self.combined_net.parameters(), lr=learning_rate)
        else:
            self.policy_net = PolicyNetwork(
                input_dim=state_dim,
                output_dim=action_dim,
                action_type='continuous',
                device=self.device
            )
            self.value_net = ValueNetwork(
                input_dim=state_dim,
                device=self.device
            )
            
            # Combined optimizer
            params = list(self.policy_net.parameters()) + list(self.value_net.parameters())
            self.optimizer = optim.Adam(params, lr=learning_rate)
        
        logger.info(f"Initialized A2C agent: combined_net={use_combined_network}")
    
    def select_action(self, state: torch.Tensor, deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Select action using policy network"""
        # Set to eval mode for inference
        if self.use_combined_network:
            self.combined_net.eval()
        else:
            self.policy_net.eval()
            self.value_net.eval()
        
        with torch.no_grad():
            if self.use_combined_network:
                policy_output, value, _ = self.combined_net(state)
                action_mean, action_std = policy_output
            else:
                action_mean, action_std = self.policy_net(state)
                value = self.value_net(state)
            
            if deterministic:
                action = action_mean
                dist = torch.distributions.Normal(action_mean, action_std)
                log_prob = dist.log_prob(action).sum(dim=-1)
            else:
                dist = torch.distributions.Normal(action_mean, action_std)
                action = dist.sample()
                log_prob = dist.log_prob(action).sum(dim=-1)
        
        return action, log_prob, value
    
    def update(self, experiences: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        Update A2C agent using collected experiences
        """
        # Set to training mode
        if self.use_combined_network:
            self.combined_net.train()
        else:
            self.policy_net.train()
            self.value_net.train()
        
        states = experiences['states'].to(self.device)
        actions = experiences['actions'].to(self.device)
        rewards = experiences['rewards'].to(self.device)
        next_states = experiences['next_states'].to(self.device)
        dones = experiences['dones'].to(self.device)
        
        # Forward pass
        if self.use_combined_network:
            policy_output, values, _ = self.combined_net(states)
            action_mean, action_std = policy_output
            _, next_values, _ = self.combined_net(next_states)
        else:
            action_mean, action_std = self.policy_net(states)
            values = self.value_net(states)
            next_values = self.value_net(next_states)
        
        # Calculate returns and advantages
        returns = rewards + config.training.gamma * next_values * (1 - dones.float())
        advantages = returns - values
        
        # Policy loss
        dist = torch.distributions.Normal(action_mean, action_std)
        log_probs = dist.log_prob(actions).sum(dim=-1)
        policy_loss = -(log_probs * advantages.detach()).mean()
        
        # Value loss
        value_loss = F.mse_loss(values, returns.detach())
        
        # Entropy loss
        entropy = dist.entropy().sum(dim=-1).mean()
        
        # Total loss
        total_loss = policy_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy
        
        # Backward pass
        self.optimizer.zero_grad()
        total_loss.backward()
        
        # Gradient clipping
        if self.use_combined_network:
            torch.nn.utils.clip_grad_norm_(self.combined_net.parameters(), self.max_grad_norm)
        else:
            torch.nn.utils.clip_grad_norm_(
                list(self.policy_net.parameters()) + list(self.value_net.parameters()),
                self.max_grad_norm
            )
        
        self.optimizer.step()
        
        # Update training statistics
        self.training_stats['episodes'] += 1
        self.training_stats['policy_loss'] = policy_loss.item()
        self.training_stats['value_loss'] = value_loss.item()
        self.training_stats['entropy'] = entropy.item()
        
        return {
            'policy_loss': policy_loss.item(),
            'value_loss': value_loss.item(),
            'entropy': entropy.item(),
            'total_loss': total_loss.item()
        }


def create_agent(agent_type: str = 'PPO', **kwargs) -> BaseAgent:
    """
    Factory function to create RL agents
    
    Args:
        agent_type: Type of agent ('PPO' or 'A2C')
        **kwargs: Agent configuration
        
    Returns:
        Initialized agent
    """
    # Get defaults from config
    training_config = config.training
    model_config = config.model
    
    # Default parameters
    params = {
        'state_dim': model_config.input_dim,
        'action_dim': model_config.output_dim,
        'learning_rate': training_config.learning_rate,
        **kwargs
    }
    
    if agent_type.upper() == 'PPO':
        # Add PPO-specific parameters
        ppo_params = {
            'clip_epsilon': training_config.clip_epsilon,
            'ppo_epochs': training_config.ppo_epochs,
            'value_loss_coef': training_config.value_loss_weight,
            'entropy_coef': training_config.entropy_weight,
            'max_grad_norm': training_config.max_grad_norm,
            **params
        }
        return PPOAgent(**ppo_params)
    
    elif agent_type.upper() == 'A2C':
        # Add A2C-specific parameters
        a2c_params = {
            'value_loss_coef': training_config.value_loss_weight,
            'entropy_coef': training_config.entropy_weight,
            'max_grad_norm': training_config.max_grad_norm,
            **params
        }
        return A2CAgent(**a2c_params)
    
    else:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: PPO, A2C")


def test_agents():
    """Test agent implementations"""
    logger.info("Testing RL agents...")
    
    # Test data
    batch_size = 4
    state_dim = 300
    action_dim = 20
    
    states = torch.randn(batch_size, state_dim)
    actions = torch.randn(batch_size, action_dim)
    rewards = torch.randn(batch_size)
    next_states = torch.randn(batch_size, state_dim)
    dones = torch.randint(0, 2, (batch_size,), dtype=torch.bool)
    log_probs = torch.randn(batch_size)
    values = torch.randn(batch_size)
    
    experiences = {
        'states': states,
        'actions': actions,
        'rewards': rewards,
        'next_states': next_states,
        'dones': dones,
        'log_probs': log_probs,
        'values': values
    }
    
    # Test PPO agent
    ppo_agent = create_agent('PPO')
    action, log_prob, value = ppo_agent.select_action(states[0:1])
    assert action.shape == (1, action_dim), f"Expected action shape (1, {action_dim}), got {action.shape}"
    assert log_prob.shape == (1,), f"Expected log_prob shape (1,), got {log_prob.shape}"
    assert value.shape == (1,), f"Expected value shape (1,), got {value.shape}"
    
    # Test update
    stats = ppo_agent.update(experiences)
    assert 'policy_loss' in stats, "Missing policy_loss in stats"
    assert 'value_loss' in stats, "Missing value_loss in stats"
    
    logger.info("✓ PPO agent test passed")
    
    # Test A2C agent
    a2c_agent = create_agent('A2C')
    action, log_prob, value = a2c_agent.select_action(states[0:1])
    assert action.shape == (1, action_dim), f"Expected action shape (1, {action_dim}), got {action.shape}"
    
    # Test update
    stats = a2c_agent.update(experiences)
    assert 'policy_loss' in stats, "Missing policy_loss in stats"
    
    logger.info("✓ A2C agent test passed")
    logger.info("All agent tests passed!")


if __name__ == "__main__":
    test_agents() 