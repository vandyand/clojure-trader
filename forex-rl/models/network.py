# models/network.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional, Dict, Any
import logging
from config.settings import config

logger = logging.getLogger(__name__)

class ForexRLNetwork(nn.Module):
    """
    Base neural network for Forex RL trading
    Architecture: 300 → 512 → 256 → 128 → 20
    
    Features:
    - Batch normalization for stable training
    - Dropout for regularization
    - Configurable activation functions
    - GPU support
    """
    
    def __init__(self, 
                 input_dim: int = 300,
                 hidden_dims: list = None,
                 output_dim: int = 20,
                 activation: str = 'relu',
                 dropout: float = 0.1,
                 batch_norm: bool = True,
                 device: str = None):
        """
        Initialize the network
        
        Args:
            input_dim: Input feature dimension (300 for our Fibonacci features)
            hidden_dims: List of hidden layer dimensions
            output_dim: Output dimension (20 for forex pairs)
            activation: Activation function ('relu', 'tanh', 'leaky_relu')
            dropout: Dropout probability
            batch_norm: Whether to use batch normalization
            device: Device to run on ('cpu', 'cuda', 'auto')
        """
        super(ForexRLNetwork, self).__init__()
        
        # Configuration
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims or config.model.hidden_dims
        self.output_dim = output_dim
        self.activation_name = activation
        self.dropout_prob = dropout
        self.use_batch_norm = batch_norm
        
        # Device setup
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        elif device is None:
            self.device = torch.device('cpu')
        else:
            self.device = torch.device(device)
        
        # Activation function
        self.activation = self._get_activation_function(activation)
        
        # Build network layers
        self.layers = nn.ModuleList()
        self.batch_norms = nn.ModuleList() if batch_norm else None
        self.dropouts = nn.ModuleList()
        
        # Input layer
        prev_dim = input_dim
        for i, hidden_dim in enumerate(self.hidden_dims):
            # Linear layer
            self.layers.append(nn.Linear(prev_dim, hidden_dim))
            
            # Batch normalization
            if batch_norm:
                self.batch_norms.append(nn.BatchNorm1d(hidden_dim))
            
            # Dropout
            self.dropouts.append(nn.Dropout(dropout))
            
            prev_dim = hidden_dim
        
        # Output layer
        self.output_layer = nn.Linear(prev_dim, output_dim)
        
        # Initialize weights
        self._initialize_weights()
        
        # Move to device
        self.to(self.device)
        
        logger.info(f"Initialized ForexRLNetwork: {input_dim} → {' → '.join(map(str, self.hidden_dims))} → {output_dim}")
        logger.info(f"Device: {self.device}, Parameters: {self.count_parameters():,}")
    
    def _get_activation_function(self, activation: str) -> nn.Module:
        """Get activation function by name"""
        activations = {
            'relu': nn.ReLU(),
            'tanh': nn.Tanh(),
            'leaky_relu': nn.LeakyReLU(0.01),
            'elu': nn.ELU(),
            'gelu': nn.GELU(),
            'swish': nn.SiLU()
        }
        
        if activation not in activations:
            raise ValueError(f"Unknown activation: {activation}. Available: {list(activations.keys())}")
        
        return activations[activation]
    
    def _initialize_weights(self):
        """Initialize network weights using Xavier/He initialization"""
        for layer in self.layers:
            if isinstance(layer, nn.Linear):
                # He initialization for ReLU-like activations
                if self.activation_name in ['relu', 'leaky_relu', 'elu']:
                    nn.init.kaiming_normal_(layer.weight, mode='fan_in', nonlinearity='relu')
                else:
                    # Xavier initialization for other activations
                    nn.init.xavier_normal_(layer.weight)
                
                # Initialize bias to small positive values
                nn.init.constant_(layer.bias, 0.01)
        
        # Output layer initialization (smaller weights for stability)
        nn.init.xavier_normal_(self.output_layer.weight, gain=0.1)
        nn.init.constant_(self.output_layer.bias, 0.0)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
            
        Returns:
            Output tensor of shape (batch_size, output_dim)
        """
        # Ensure input is on correct device
        if x.device != self.device:
            x = x.to(self.device)
        
        # Forward through hidden layers
        for i, layer in enumerate(self.layers):
            x = layer(x)
            
            # Batch normalization
            if self.use_batch_norm:
                x = self.batch_norms[i](x)
            
            # Activation
            x = self.activation(x)
            
            # Dropout
            x = self.dropouts[i](x)
        
        # Output layer (no activation - will be handled by agent)
        x = self.output_layer(x)
        
        return x
    
    def count_parameters(self) -> int:
        """Count total number of trainable parameters"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_device(self) -> torch.device:
        """Get the device the model is on"""
        return self.device
    
    def save_checkpoint(self, filepath: str, metadata: Dict[str, Any] = None):
        """Save model checkpoint"""
        checkpoint = {
            'model_state_dict': self.state_dict(),
            'model_config': {
                'input_dim': self.input_dim,
                'hidden_dims': self.hidden_dims,
                'output_dim': self.output_dim,
                'activation': self.activation_name,
                'dropout': self.dropout_prob,
                'batch_norm': self.use_batch_norm
            },
            'metadata': metadata or {}
        }
        
        torch.save(checkpoint, filepath)
        logger.info(f"Model checkpoint saved to {filepath}")
    
    @classmethod
    def load_checkpoint(cls, filepath: str, device: str = None):
        """Load model from checkpoint"""
        checkpoint = torch.load(filepath, map_location='cpu')
        
        # Create model with saved configuration
        model = cls(
            input_dim=checkpoint['model_config']['input_dim'],
            hidden_dims=checkpoint['model_config']['hidden_dims'],
            output_dim=checkpoint['model_config']['output_dim'],
            activation=checkpoint['model_config']['activation'],
            dropout=checkpoint['model_config']['dropout'],
            batch_norm=checkpoint['model_config']['batch_norm'],
            device=device
        )
        
        # Load state dict
        model.load_state_dict(checkpoint['model_state_dict'])
        
        logger.info(f"Model loaded from {filepath}")
        return model, checkpoint.get('metadata', {})


class PolicyNetwork(ForexRLNetwork):
    """
    Policy network for RL agent
    Outputs action probabilities or continuous actions
    """
    
    def __init__(self, 
                 input_dim: int = 300,
                 hidden_dims: list = None,
                 output_dim: int = 20,
                 action_type: str = 'continuous',
                 **kwargs):
        """
        Initialize policy network
        
        Args:
            action_type: 'continuous' for continuous actions, 'discrete' for discrete
        """
        super().__init__(input_dim, hidden_dims, output_dim, **kwargs)
        
        self.action_type = action_type
        
        if action_type == 'continuous':
            # For continuous actions, output mean and log_std
            self.action_mean = nn.Linear(output_dim, output_dim)
            self.action_log_std = nn.Parameter(torch.zeros(output_dim))
            
            # Initialize action head
            nn.init.xavier_normal_(self.action_mean.weight, gain=0.01)
            nn.init.constant_(self.action_mean.bias, 0.0)
            
        elif action_type == 'discrete':
            # For discrete actions, output logits
            self.action_head = nn.Linear(output_dim, output_dim)
            nn.init.xavier_normal_(self.action_head.weight, gain=0.01)
            nn.init.constant_(self.action_head.bias, 0.0)
        
        logger.info(f"Initialized PolicyNetwork with {action_type} actions")
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass for policy network
        
        Returns:
            For continuous: (action_mean, action_std)
            For discrete: (action_logits, None)
        """
        # Get features from base network
        features = super().forward(x)
        
        if self.action_type == 'continuous':
            # Continuous actions: output mean and std
            action_mean = self.action_mean(features)
            action_std = torch.exp(self.action_log_std.expand_as(action_mean))
            
            # Clamp to reasonable ranges
            action_mean = torch.tanh(action_mean)  # [-1, 1] range
            action_std = torch.clamp(action_std, min=0.01, max=2.0)
            
            return action_mean, action_std
            
        else:  # discrete
            # Discrete actions: output logits
            action_logits = self.action_head(features)
            return action_logits, None
    
    def sample_action(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Sample action from policy
        
        Returns:
            action: Sampled action
            log_prob: Log probability of the action
        """
        if self.action_type == 'continuous':
            action_mean, action_std = self.forward(x)
            
            # Create normal distribution
            dist = torch.distributions.Normal(action_mean, action_std)
            
            # Sample action
            action = dist.sample()
            log_prob = dist.log_prob(action).sum(dim=-1)
            
            return action, log_prob
            
        else:  # discrete
            action_logits, _ = self.forward(x)
            
            # Create categorical distribution
            dist = torch.distributions.Categorical(logits=action_logits)
            
            # Sample action
            action = dist.sample()
            log_prob = dist.log_prob(action)
            
            return action, log_prob


class ValueNetwork(ForexRLNetwork):
    """
    Value network for RL agent
    Outputs state value estimates
    """
    
    def __init__(self, 
                 input_dim: int = 300,
                 hidden_dims: list = None,
                 **kwargs):
        """Initialize value network (output_dim=1 for value estimation)"""
        super().__init__(input_dim, hidden_dims, output_dim=1, **kwargs)
        
        logger.info("Initialized ValueNetwork")
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for value network
        
        Returns:
            State value estimate
        """
        # Get value from base network
        value = super().forward(x)
        
        # Squeeze to remove last dimension (batch_size, 1) -> (batch_size,)
        return value.squeeze(-1)


class CombinedNetwork(nn.Module):
    """
    Combined policy and value network for efficiency
    Shares feature extraction layers
    """
    
    def __init__(self,
                 input_dim: int = 300,
                 hidden_dims: list = None,
                 output_dim: int = 20,
                 action_type: str = 'continuous',
                 **kwargs):
        """Initialize combined network"""
        super().__init__()
        
        # Shared feature extractor
        self.feature_extractor = ForexRLNetwork(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            output_dim=hidden_dims[-1] if hidden_dims else 128,  # Feature dimension
            **kwargs
        )
        
        # Policy head
        feature_dim = hidden_dims[-1] if hidden_dims else 128
        self.policy_head = nn.Linear(feature_dim, output_dim)
        
        # Value head
        self.value_head = nn.Linear(feature_dim, 1)
        
        # Action type specific layers
        self.action_type = action_type
        if action_type == 'continuous':
            self.action_log_std = nn.Parameter(torch.zeros(output_dim))
        
        # Initialize heads
        nn.init.xavier_normal_(self.policy_head.weight, gain=0.01)
        nn.init.constant_(self.policy_head.bias, 0.0)
        nn.init.xavier_normal_(self.value_head.weight)
        nn.init.constant_(self.value_head.bias, 0.0)
        
        logger.info(f"Initialized CombinedNetwork with {action_type} actions")
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass for combined network
        
        Returns:
            policy_output: Policy network output
            value: State value estimate
            features: Shared features (for analysis)
        """
        # Extract shared features
        features = self.feature_extractor(x)
        
        # Policy output
        policy_logits = self.policy_head(features)
        
        # Value output
        value = self.value_head(features).squeeze(-1)
        
        if self.action_type == 'continuous':
            # For continuous actions, apply tanh and get std
            policy_mean = torch.tanh(policy_logits)
            policy_std = torch.exp(self.action_log_std.expand_as(policy_mean))
            policy_std = torch.clamp(policy_std, min=0.01, max=2.0)
            policy_output = (policy_mean, policy_std)
        else:
            # For discrete actions, return logits
            policy_output = policy_logits
        
        return policy_output, value, features
    
    def get_device(self) -> torch.device:
        """Get the device the model is on"""
        return self.feature_extractor.get_device()


# Utility functions
def create_network(network_type: str = 'policy', **kwargs) -> nn.Module:
    """
    Factory function to create networks
    
    Args:
        network_type: 'policy', 'value', 'combined', or 'base'
        **kwargs: Network configuration
        
    Returns:
        Initialized network
    """
    if network_type == 'policy':
        return PolicyNetwork(**kwargs)
    elif network_type == 'value':
        return ValueNetwork(**kwargs)
    elif network_type == 'combined':
        return CombinedNetwork(**kwargs)
    elif network_type == 'base':
        return ForexRLNetwork(**kwargs)
    else:
        raise ValueError(f"Unknown network type: {network_type}")


def test_network_forward_pass():
    """Test network forward pass with sample data"""
    logger.info("Testing network forward pass...")
    
    # Create sample input
    batch_size = 32
    input_dim = 300
    x = torch.randn(batch_size, input_dim)
    
    # Test base network
    base_net = ForexRLNetwork()
    output = base_net(x)
    assert output.shape == (batch_size, 20), f"Expected (32, 20), got {output.shape}"
    logger.info(f"✓ Base network output shape: {output.shape}")
    
    # Test policy network
    policy_net = PolicyNetwork(action_type='continuous')
    action_mean, action_std = policy_net(x)
    assert action_mean.shape == (batch_size, 20), f"Expected (32, 20), got {action_mean.shape}"
    assert action_std.shape == (batch_size, 20), f"Expected (32, 20), got {action_std.shape}"
    logger.info(f"✓ Policy network output shapes: {action_mean.shape}, {action_std.shape}")
    
    # Test value network
    value_net = ValueNetwork()
    value = value_net(x)
    assert value.shape == (batch_size,), f"Expected (32,), got {value.shape}"
    logger.info(f"✓ Value network output shape: {value.shape}")
    
    # Test combined network
    combined_net = CombinedNetwork()
    policy_output, value, features = combined_net(x)
    action_mean, action_std = policy_output
    assert action_mean.shape == (batch_size, 20), f"Expected (32, 20), got {action_mean.shape}"
    assert value.shape == (batch_size,), f"Expected (32,), got {value.shape}"
    logger.info(f"✓ Combined network output shapes: {action_mean.shape}, {value.shape}, {features.shape}")
    
    logger.info("All network tests passed!")


if __name__ == "__main__":
    # Run tests
    test_network_forward_pass() 