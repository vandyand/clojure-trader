import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import sys
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from crypto_rl.constants import CRYPTO_PAIRS_BY_LIQUIDITY

# Path to saved models
MODELS_DIR = Path(os.path.join(os.path.dirname(__file__), "models"))
FUSION_AUTOENCODER_PATH = Path(os.path.join(os.path.dirname(__file__), "models", "fusion_autoencoder.pt"))

# Import ScaledTanhInput for autoencoder
class ScaledTanhInput(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))
    
    def forward(self, x):
        return torch.tanh(self.scale * x + self.bias)

# Autoencoder model definition for loading
class AutoencoderModel(nn.Module):
    def __init__(self, n_features, bottleneck_dim=64):
        super().__init__()
        # Define layer sizes with progressive compression to match trained model
        self.bottleneck_dim = bottleneck_dim
        hidden_dim1 = n_features // 2
        hidden_dim2 = n_features // 4
        
        # Input scaling layer
        self.input_layer = ScaledTanhInput(n_features)
        
        # Encoder layers with LeakyReLU activation (matching trained model)
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Linear(hidden_dim2, bottleneck_dim),
            nn.Tanh(),  # Keep tanh in bottleneck for bounded representation
            nn.BatchNorm1d(bottleneck_dim)
        )
        
        # Decoder layers with LeakyReLU activation (matching trained model)
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Linear(hidden_dim2, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Linear(hidden_dim1, n_features)
        )
    
    def forward(self, x):
        # Apply scaled tanh input transformation
        x = self.input_layer(x)
        # Encode
        z = self.encoder(x)
        # Decode
        return self.decoder(z)
    
    def encode(self, x):
        x = self.input_layer(x)
        return self.encoder(x)

class PolicyNetwork(nn.Module):
    """
    RL policy network (Actor) that takes fusion autoencoder's bottleneck as input
    and outputs parameters for action distributions (means) for 20 crypto pairs.
    """
    def __init__(self, bottleneck_dim: int = 64, n_instruments: int = 20, hidden_dims: List[int] = [256, 128]):
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
        
        # Initialize log_std_devs with a more conservative value
        self.log_std_devs = nn.Parameter(torch.full((n_instruments,), -1.0))
        
        # Initialize weights with more conservative values
        self.apply(self._init_weights)
        
    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            # Use less conservative initialization to encourage exploration
            # Changed from gain=0.01 to gain=0.5
            nn.init.xavier_normal_(module.weight, gain=0.5)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with validation and robust handling.
        """
        # Validate input
        if torch.isnan(x).any() or torch.isinf(x).any():
            print("Warning: NaN/Inf detected in policy input. Replacing with zeros.")
            x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Forward pass
        x = self.hidden_layers(x)
        means = self.mean_head(x)
        
        # Clip means to prevent extreme values
        means = torch.clamp(means, -5.0, 5.0)
        
        return means

    def get_action_distribution(self, means: torch.Tensor) -> torch.distributions.Normal:
        """
        Creates a Normal distribution with robust handling.
        """
        # Ensure means are valid
        if torch.isnan(means).any() or torch.isinf(means).any():
            print("Warning: NaN/Inf detected in action means. Replacing with zeros.")
            means = torch.nan_to_num(means, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Get std_devs with a minimum value to prevent collapse
        std_devs = torch.exp(self.log_std_devs).clamp(min=1e-6)
        
        # Expand std_devs if needed
        if means.ndim > 1 and std_devs.ndim == 1:
            std_devs = std_devs.unsqueeze(0).expand_as(means)
        
        return torch.distributions.Normal(means, std_devs)

class ValueNetwork(nn.Module):
    """
    Value network (Critic) that estimates the value of states.
    """
    def __init__(self, bottleneck_dim: int = 64, hidden_dims: List[int] = [256, 128]):
        super().__init__()
        
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
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.xavier_normal_(module.weight, gain=0.5)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with validation.
        """
        # Validate input
        if torch.isnan(x).any() or torch.isinf(x).any():
            print("Warning: NaN/Inf detected in value input. Replacing with zeros.")
            x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Forward pass
        x = self.hidden_layers(x)
        value = self.value_head(x)
        
        return value

class FusionAutoencoder:
    """
    Wrapper for the fusion autoencoder that handles loading and encoding.
    """
    def __init__(self, model_path: str = str(FUSION_AUTOENCODER_PATH)):
        self.model_path = model_path
        self.model = None
        self.n_features = None
        self.bottleneck_dim = None
        
        # Try to load the model
        self._load_model()
    
    def _load_model(self):
        """Load the fusion autoencoder model."""
        try:
            if os.path.exists(self.model_path):
                checkpoint = torch.load(self.model_path, map_location='cpu')
                
                # Extract model parameters
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                    # Infer dimensions from state dict
                    for key in state_dict.keys():
                        if 'encoder.0.weight' in key:
                            self.n_features = state_dict[key].shape[1]
                            break
                    
                    # Create model with inferred dimensions
                    if self.n_features is not None:
                        self.bottleneck_dim = 149  # Fixed bottleneck size
                        self.model = AutoencoderModel(self.n_features, self.bottleneck_dim)
                        self.model.load_state_dict(state_dict)
                        self.model.eval()
                        print(f"Loaded fusion autoencoder with {self.n_features} input features and {self.bottleneck_dim} bottleneck")
                    else:
                        print("Could not infer model dimensions from checkpoint")
                else:
                    print("Checkpoint does not contain model_state_dict")
            else:
                print(f"Model file not found at {self.model_path}")
                
        except Exception as e:
            print(f"Error loading fusion autoencoder: {e}")
            print("Will use identity mapping (no autoencoder)")
    
    def validate_and_normalize(self, features: torch.Tensor) -> torch.Tensor:
        """
        Validate and normalize input features.
        """
        # Check for NaN/Inf values
        if torch.isnan(features).any() or torch.isinf(features).any():
            print("Warning: NaN/Inf detected in features. Replacing with zeros.")
            features = torch.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Normalize features to [-1, 1] range using tanh scaling
        features = torch.tanh(features)
        
        return features
    
    def encode(self, features: torch.Tensor) -> torch.Tensor:
        """
        Encode features through the autoencoder.
        """
        if self.model is None:
            # If no autoencoder, use identity mapping
            return features
        
        try:
            # Validate and normalize features
            features = self.validate_and_normalize(features)
            
            # Encode through autoencoder
            with torch.no_grad():
                encoded = self.model.encode(features)
            
            # Validate output
            if torch.isnan(encoded).any() or torch.isinf(encoded).any():
                print("Warning: NaN/Inf detected in encoded features. Replacing with zeros.")
                encoded = torch.nan_to_num(encoded, nan=0.0, posinf=0.0, neginf=0.0)
            
            return encoded
            
        except Exception as e:
            print(f"Error encoding features: {e}")
            # Fallback to identity mapping
            return features

class RewardCalculator:
    """
    Implements the reward mechanism as specified in reward-info.md
    Now supports both long and short positions.
    """
    def __init__(self, n_instruments: int = 20, beta: float = 0.95):
        self.n_instruments = n_instruments
        self.beta = beta
        # Initialize DSR tracking variables
        self.mu_prev = 0.0  # Previous mean return
        self.sigma_sq_prev = 0.0001  # Previous variance (0.01^2)
        
        # Initialize tracking variables for Differential Sharpe Ratio
        self.mu = 0.0  # Mean return
        self.sigma_sq = 0.0001  # Initial variance (0.01²)
        
    def normalize_positions(self, raw_outputs: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Normalize positions using Dirichlet-inspired approach as in reward-info.md.
        
        Args:
            raw_outputs: Raw model outputs [n_instruments]
            
        Returns:
            normalized_positions: Normalized positions [n_instruments]
            alpha_0: Total concentration parameter
        """
        # Calculate alpha values (position confidence)
        long_positions = np.maximum(raw_outputs, 0)
        short_positions = np.maximum(-raw_outputs, 0)
        alpha = long_positions + short_positions
        
        # Calculate total concentration parameter
        alpha_0 = np.sum(alpha) + 1e-8
        
        # Normalize positions by alpha_0
        normalized_positions = alpha / alpha_0
        
        # Restore signs (long positions positive, short positions negative)
        signs = np.sign(raw_outputs)
        normalized_positions = normalized_positions * signs
        
        return normalized_positions, alpha_0
    
    def position_entropy(self, positions: np.ndarray) -> Tuple[float, float]:
        """
        Calculate position entropy using absolute values of positions.
        
        Args:
            positions: Position sizes [n_instruments] (can be positive or negative)
            
        Returns:
            entropy: Position entropy
            normalized_entropy: Entropy normalized by log(n_instruments)
        """
        abs_pos = np.abs(positions)
        p = abs_pos / (np.sum(abs_pos) + 1e-8)
        entropy = -np.sum(p * np.log(p + 1e-8))
        normalized_entropy = entropy / np.log(len(positions)) if len(positions) > 1 else 0.0
        return entropy, normalized_entropy
    
    def apply_entropy_penalty(self, positions: np.ndarray, normalized_entropy: float) -> Tuple[np.ndarray, float]:
        """
        Apply entropy-based scaling to positions while preserving signs.
        Uses the exact formula from reward-info.md.
        
        Args:
            positions: Position sizes [n_instruments] (can be positive or negative)
            normalized_entropy: Normalized entropy value
            
        Returns:
            scaled_positions: Scaled positions [n_instruments]
            scaling_factor: Applied scaling factor
        """
        # Use the exact formula from reward-info.md: Scaling Factor = 1 - Normalized Entropy
        scaling_factor = 1.0 - normalized_entropy
        return positions * scaling_factor, scaling_factor
    
    def portfolio_return(self, final_positions: np.ndarray, price_changes: np.ndarray) -> float:
        """
        Calculate portfolio return from positions and price changes.
        Works with both long and short positions.
        
        Args:
            final_positions: Position sizes [n_instruments] (can be positive or negative)
            price_changes: Price changes [n_instruments]
            
        Returns:
            Portfolio return
        """
        return np.sum(final_positions * price_changes)
    
    def calculate_dsr(self, R_t: float) -> float:
        """
        Calculate Differential Sharpe Ratio (DSR) using exponential moving averages.
        
        Args:
            R_t: Current portfolio return
            
        Returns:
            Differential Sharpe Ratio
        """
        # Update mean and variance using exponential moving average
        delta = R_t - self.mu_prev
        self.mu = self.mu_prev + self.beta * delta
        self.sigma_sq = self.sigma_sq_prev + self.beta * (R_t**2 - self.sigma_sq_prev)
        
        # Calculate DSR
        numerator = self.beta * delta - 0.5 * (self.beta**2) * self.sigma_sq_prev
        denominator = (self.sigma_sq_prev + self.beta * delta**2)**1.5 + 1e-12
        
        dsr = numerator / denominator
        
        # Update previous values
        self.mu_prev = self.mu
        self.sigma_sq_prev = self.sigma_sq
        
        return dsr
    
    def confidence_weighted_reward(self, dsr: float, alpha_0: float) -> Tuple[float, float]:
        """
        Apply confidence weighting based on Dirichlet concentration parameter α₀.
        
        Formula: Weight = 1 - 1/(α₀ + 1)
        
        Args:
            dsr: Differential Sharpe ratio
            alpha_0: Total concentration parameter (sum of all α values)
            
        Returns:
            weighted_reward: Confidence-weighted reward
            confidence: Confidence value
        """
        confidence = 1.0 - 1.0 / (alpha_0 + 1.0)
        return dsr * confidence, confidence
    
    def calculate_reward(self, 
                        raw_outputs: np.ndarray, 
                        price_changes: np.ndarray) -> Dict:
        """
        Simplified reward calculation focusing on direction prediction.
        
        Args:
            raw_outputs: Model outputs for position sizing [n_instruments]
            price_changes: Percentage price changes for instruments [n_instruments]
            
        Returns:
            Dictionary containing all intermediate calculations and final reward
        """
        # 1. Normalize positions using Dirichlet-inspired approach
        positions, alpha_0 = self.normalize_positions(raw_outputs)
        
        # 2. Calculate entropy penalty
        entropy, norm_entropy = self.position_entropy(positions)
        final_positions, scaling = self.apply_entropy_penalty(positions, norm_entropy)
        
        # 3. Calculate portfolio return
        R_t = self.portfolio_return(final_positions, price_changes)
        
        # 4. Calculate DSR using the correct Differential Sharpe Ratio formula
        dsr = self.calculate_dsr(R_t)
        
        # 5. Calculate confidence-weighted reward using alpha_0
        reward, confidence = self.confidence_weighted_reward(dsr, alpha_0)
        
        # 6. Clip reward to prevent extreme values
        clipped_reward = np.clip(reward, -10.0, 10.0)
        
        return {
            'raw_outputs': raw_outputs,
            'normalized_positions': positions,
            'alpha_0': alpha_0,
            'entropy': entropy,
            'normalized_entropy': norm_entropy,
            'final_positions': final_positions,
            'scaling_factor': scaling,
            'portfolio_return': R_t,
            'differential_sharpe': dsr,
            'confidence': confidence,
            'reward': reward,
            'clipped_reward': clipped_reward
        }

class CryptoRLTrader:
    """
    Main RL trader class that combines policy network, value network, and autoencoder.
    """
    def __init__(self, 
                 actor_lr: float = 1e-4,
                 critic_lr: float = 1e-3,
                 gamma: float = 0.99,
                 entropy_weight: float = 0.01,
                 autoencoder_path: str = 'models/fusion_autoencoder.pt',
                 n_instruments: int = 20):
        """
        Initialize the RL trader.
        
        Args:
            actor_lr: Learning rate for actor (policy) network
            critic_lr: Learning rate for critic (value) network
            gamma: Discount factor
            entropy_weight: Weight for entropy regularization
            autoencoder_path: Path to fusion autoencoder model
            n_instruments: Number of crypto instruments
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.gamma = gamma
        self.entropy_weight = entropy_weight
        self.n_instruments = n_instruments
        
        # Initialize autoencoder
        self.autoencoder = FusionAutoencoder(autoencoder_path)
        
        # Initialize networks (will be set up after we know input dimensions)
        self.policy_network = None
        self.value_network = None
        self.policy_optimizer = None
        self.value_optimizer = None
        
        # Initialize reward calculator
        self.reward_calculator = RewardCalculator(n_instruments=n_instruments)
        
        print(f"Initialized CryptoRLTrader on device: {self.device}")
    
    def _initialize_networks(self, input_dim: int):
        """Initialize policy and value networks with the correct input dimensions."""
        bottleneck_dim = self.autoencoder.bottleneck_dim or input_dim
        
        # Initialize policy network
        self.policy_network = PolicyNetwork(
            bottleneck_dim=bottleneck_dim,
            n_instruments=self.n_instruments
        ).to(self.device)
        
        # Initialize value network
        self.value_network = ValueNetwork(
            bottleneck_dim=bottleneck_dim
        ).to(self.device)
        
        # Initialize optimizers
        self.policy_optimizer = optim.Adam(self.policy_network.parameters(), lr=1e-4)
        self.value_optimizer = optim.Adam(self.value_network.parameters(), lr=1e-3)
        
        print(f"Initialized networks with bottleneck_dim={bottleneck_dim}")
    
    def encode_state(self, state: torch.Tensor) -> torch.Tensor:
        """
        Encode state through the fusion autoencoder.
        
        Args:
            state: Input state tensor [batch_size, n_features]
            
        Returns:
            Encoded state tensor [batch_size, bottleneck_dim]
        """
        if self.autoencoder.model is None:
            # If no autoencoder, use identity mapping
            return state
        
        return self.autoencoder.encode(state)
    
    def get_action(self, state: torch.Tensor, training: bool = True) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get action from the policy network.
        
        Args:
            state: Input state tensor [batch_size, n_features]
            training: Whether in training mode
            
        Returns:
            actions: Action tensor [batch_size, n_instruments]
            log_probs: Log probabilities tensor [batch_size, n_instruments]
        """
        # Initialize networks if not done yet
        if self.policy_network is None:
            self._initialize_networks(state.shape[1])
        
        # Encode state through autoencoder
        encoded_state = self.encode_state(state)
        
        # Get action means from policy network
        means = self.policy_network(encoded_state)
        
        # Create action distribution
        action_dist = self.policy_network.get_action_distribution(means)
        
        if training:
            # Sample actions during training
            actions = action_dist.sample()
            log_probs = action_dist.log_prob(actions)
        else:
            # Use means during evaluation
            actions = means
            log_probs = action_dist.log_prob(actions)
        
        return actions, log_probs
    
    def update_policy(self, 
                     states: torch.Tensor,
                     actions: torch.Tensor,
                     rewards: torch.Tensor,
                     next_states: torch.Tensor,
                     dones: torch.Tensor) -> Dict[str, float]:
        """
        Update the policy and value networks using PPO-style updates.
        
        Args:
            states: Current states [batch_size, n_features]
            actions: Actions taken [batch_size, n_instruments]
            rewards: Rewards received [batch_size]
            next_states: Next states [batch_size, n_features]
            dones: Done flags [batch_size]
            
        Returns:
            Dictionary with loss values
        """
        # Initialize networks if not done yet
        if self.policy_network is None:
            self._initialize_networks(states.shape[1])
        
        # Encode states
        encoded_states = self.encode_state(states)
        encoded_next_states = self.encode_state(next_states)
        
        # Get current value estimates
        current_values = self.value_network(encoded_states).squeeze()
        
        # Get next value estimates
        with torch.no_grad():
            next_values = self.value_network(encoded_next_states).squeeze()
        
        # Calculate target values
        target_values = rewards + self.gamma * next_values * (1 - dones)
        
        # Calculate value loss
        value_loss = nn.MSELoss()(current_values, target_values)
        
        # Calculate policy loss (simplified PPO)
        action_dist = self.policy_network.get_action_distribution(
            self.policy_network(encoded_states)
        )
        log_probs = action_dist.log_prob(actions).sum(dim=1)
        
        # Calculate advantages (simplified)
        advantages = rewards - current_values.detach()
        
        # Policy loss with entropy regularization
        policy_loss = -(log_probs * advantages).mean()
        entropy = action_dist.entropy().mean()
        total_policy_loss = policy_loss - self.entropy_weight * entropy
        
        # Update networks
        self.policy_optimizer.zero_grad()
        total_policy_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_network.parameters(), 0.5)
        self.policy_optimizer.step()
        
        self.value_optimizer.zero_grad()
        value_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.value_network.parameters(), 0.5)
        self.value_optimizer.step()
        
        return {
            'actor_loss': total_policy_loss.item(),
            'critic_loss': value_loss.item(),
            'entropy': entropy.item()
        }
    
    def save_model(self, path: str):
        """Save the model to a file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        torch.save({
            'policy_state_dict': self.policy_network.state_dict() if self.policy_network else None,
            'value_state_dict': self.value_network.state_dict() if self.value_network else None,
            'policy_optimizer_state_dict': self.policy_optimizer.state_dict() if self.policy_optimizer else None,
            'value_optimizer_state_dict': self.value_optimizer.state_dict() if self.value_optimizer else None,
            'n_instruments': self.n_instruments,
            'gamma': self.gamma,
            'entropy_weight': self.entropy_weight
        }, path)
        
        print(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load the model from a file."""
        if not os.path.exists(path):
            print(f"Model file not found: {path}")
            return
        
        checkpoint = torch.load(path, map_location=self.device)
        
        # Initialize networks if needed
        if self.policy_network is None:
            # We need to know the input dimension to initialize networks
            # This will be set when we first call get_action
            pass
        
        # Load state dicts
        if checkpoint['policy_state_dict'] and self.policy_network:
            self.policy_network.load_state_dict(checkpoint['policy_state_dict'])
        
        if checkpoint['value_state_dict'] and self.value_network:
            self.value_network.load_state_dict(checkpoint['value_state_dict'])
        
        if checkpoint['policy_optimizer_state_dict'] and self.policy_optimizer:
            self.policy_optimizer.load_state_dict(checkpoint['policy_optimizer_state_dict'])
        
        if checkpoint['value_optimizer_state_dict'] and self.value_optimizer:
            self.value_optimizer.load_state_dict(checkpoint['value_optimizer_state_dict'])
        
        print(f"Model loaded from {path}") 