import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import sys
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from constants import PAIRS_BY_LIQUIDITY_OANDA

# Path to saved models
MODELS_DIR = Path(os.path.join(os.path.dirname(__file__), "models"))
# FUSION_AUTOENCODER_PATH = MODELS_DIR / "fusion_autoencoder.pt" # Old path
FUSION_AUTOENCODER_PATH = Path(os.path.join(os.path.dirname(__file__), "models", "fusion_autoencoder.pt")) # New path to rl/models

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
    and outputs parameters for action distributions (means) for 20 currency pairs.
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

    def sample_action(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Samples an action from the policy distribution and returns the action and its log probability.
        Args:
            state: Input state [batch_size, bottleneck_dim] or [bottleneck_dim]
        Returns:
            action: Sampled action [batch_size, n_instruments] or [n_instruments]
            log_prob: Log probability of the sampled action [batch_size, n_instruments] or [n_instruments]
        """
        means = self.forward(state)
        dist = self.get_action_distribution(means)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        # Sum log_prob across instruments if treating them as independent components of a multivariate action
        # For A2C, it's common to sum the log_probs.
        if log_prob.ndim > 1:
            log_prob = log_prob.sum(dim=-1) 
        return action, log_prob

class ValueNetwork(nn.Module):
    """
    Critic network that estimates the value of a state V(s).
    Input is the fusion autoencoder's bottleneck representation.
    Output is a single scalar value.
    """
    def __init__(self, bottleneck_dim: int = 64, hidden_dims: List[int] = [256, 128]):
        super().__init__()
        self.bottleneck_dim = bottleneck_dim
        
        layers = []
        input_dim = bottleneck_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.LeakyReLU(0.2))
            layers.append(nn.LayerNorm(hidden_dim))
            input_dim = hidden_dim
            
        self.hidden_layers = nn.Sequential(*layers)
        self.value_head = nn.Linear(input_dim, 1) # Output a single value
        
        self.apply(self._init_weights)
        
    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            # Orthogonal initialization is common for policy/value networks
            nn.init.orthogonal_(module.weight, gain=1.0) # Gain 1 for value functions often works well
            if module.bias is not None:
                nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the value network.
        
        Args:
            x: Fusion autoencoder bottleneck representation [batch_size, bottleneck_dim]
            
        Returns:
            Estimated state value V(s) [batch_size, 1]
        """
        x = self.hidden_layers(x)
        value = self.value_head(x)
        return value

class FusionAutoencoder:
    """Helper class to load and use the fusion autoencoder"""
    def __init__(self, model_path: str = str(FUSION_AUTOENCODER_PATH)):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_info = torch.load(model_path, map_location=self.device)
        
        # Extract model parameters
        self.n_features = self.model_info['n_features']
        self.bottleneck_dim = self.model_info['bottleneck_dim']
        self.feature_names = self.model_info['feature_names']
        self.data_mean = torch.tensor(self.model_info['data_mean'], device=self.device)
        self.data_std = torch.tensor(self.model_info['data_std'], device=self.device)
        
        # Create model
        self.model = AutoencoderModel(self.n_features, self.bottleneck_dim).to(self.device)
        
        # Load state dictionary - need to filter out data_mean and data_std
        state_dict = self.model_info['state_dict']
        # Filter out the data_mean and data_std from the state_dict
        model_state_dict = {k: v for k, v in state_dict.items() 
                           if k not in ['data_mean', 'data_std']}
        
        # Load the filtered state dictionary
        self.model.load_state_dict(model_state_dict)
        
        # Set to evaluation mode
        self.model.eval()
        
        print(f"Loaded fusion autoencoder with {self.n_features} features and {self.bottleneck_dim} bottleneck dimensions")
        
    def validate_and_normalize(self, features: torch.Tensor) -> torch.Tensor:
        """
        Validate and normalize input features.
        
        Args:
            features: Input features [batch_size, n_features]
            
        Returns:
            Normalized features
        """
        # Check for NaN/Inf
        if torch.isnan(features).any() or torch.isinf(features).any():
            print("Warning: NaN/Inf detected in input features. Replacing with zeros.")
            features = torch.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Clip extreme values
        features = torch.clamp(features, -10.0, 10.0)
        
        # Normalize
        features_normalized = (features - self.data_mean) / (self.data_std + 1e-8)
        
        # Final validation
        if torch.isnan(features_normalized).any() or torch.isinf(features_normalized).any():
            print("Warning: NaN/Inf detected after normalization. Replacing with zeros.")
            features_normalized = torch.nan_to_num(features_normalized, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features_normalized
        
    def encode(self, features: torch.Tensor) -> torch.Tensor:
        """
        Encode market features using the fusion autoencoder.
        
        Args:
            features: Market features [batch_size, n_features] or [n_features]
            
        Returns:
            Bottleneck representation [batch_size, bottleneck_dim] or [bottleneck_dim]
        """
        # Add batch dimension if needed
        single_sample = False
        if features.dim() == 1:
            single_sample = True
            features = features.unsqueeze(0)
        
        # Check input dimensions
        if features.shape[1] != self.n_features:
            raise ValueError(f"Expected {self.n_features} features, got {features.shape[1]}")
        
        # Validate and normalize input data
        features_normalized = self.validate_and_normalize(features)
        
        # Encode
        with torch.no_grad():
            bottleneck = self.model.encode(features_normalized)
        
            # Final validation of encoded state
            if torch.isnan(bottleneck).any() or torch.isinf(bottleneck).any():
                print("Warning: NaN/Inf detected in encoded state. Replacing with zeros.")
                bottleneck = torch.nan_to_num(bottleneck, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Remove batch dimension if input was a single sample
        if single_sample:
            bottleneck = bottleneck.squeeze(0)
            
        return bottleneck

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
        Calculate Differential Sharpe Ratio (DSR) as defined in reward-info.md.
        
        Formula: ΔS_t = [β(R_t - μ_{t-1}) - 0.5β²σ²_{t-1}] / (σ²_{t-1} + β(R_t - μ_{t-1})²)^(3/2)
        
        Args:
            R_t: Current portfolio return (single value)
            
        Returns:
            DSR value
        """
        # Validate input
        if np.isnan(R_t) or np.isinf(R_t):
            print("Warning: NaN/Inf detected in return. Replacing with zero.")
            R_t = 0.0
        
        # Calculate DSR using the correct formula
        delta = R_t - self.mu_prev
        
        # Numerator: β(R_t - μ_{t-1}) - 0.5β²σ²_{t-1}
        numerator = self.beta * delta - 0.5 * (self.beta ** 2) * self.sigma_sq_prev
        
        # Denominator: (σ²_{t-1} + β(R_t - μ_{t-1})²)^(3/2)
        denominator = (self.sigma_sq_prev + self.beta * (delta ** 2)) ** 1.5
        
        # Avoid division by zero
        if abs(denominator) < 1e-12:
            return 0.0
        
        # Calculate DSR
        dsr = numerator / denominator
        
        # Handle NaN/Inf
        if np.isnan(dsr) or np.isinf(dsr):
            return 0.0
            
        # Update tracking variables for next iteration (after DSR calculation)
        self.mu_prev = self.mu_prev + self.beta * delta
        self.sigma_sq_prev = self.sigma_sq_prev + self.beta * (R_t ** 2 - self.sigma_sq_prev)
            
        return float(dsr)
    
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
        Complete pipeline from raw model outputs to reward calculation.
        Now supports both long and short positions.
        
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
            'positions': positions,
            'alpha_0': alpha_0,
            'position_entropy': entropy,
            'normalized_entropy': norm_entropy,
            'scaling_factor': scaling,
            'final_positions': final_positions,
            'portfolio_return': R_t,
            'differential_sharpe': dsr,
            'confidence_weight': confidence,
            'final_reward': reward,
            'clipped_reward': clipped_reward
        }

class RLTrader:
    """
    RL Trader using A2C (Advantage Actor-Critic) with support for both long and short positions.
    """
    def __init__(self, 
                 actor_lr: float = 1e-4,
                 critic_lr: float = 1e-3,
                gamma: float = 0.99,
                 entropy_weight: float = 0.01,
                 autoencoder_path: str = 'models/fusion_autoencoder.pt',
                 n_instruments: int = 20):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.gamma = gamma
        self.entropy_weight = entropy_weight
        self.actor_lr = actor_lr
        self.critic_lr = critic_lr
        self.autoencoder_loaded = False
        self.autoencoder = None
        self.state_dim = None
        self.n_instruments = n_instruments

        # Try to load autoencoder
        try:
            self.autoencoder = FusionAutoencoder(autoencoder_path)
            self.autoencoder_loaded = True
            self.state_dim = self.autoencoder.bottleneck_dim
        except Exception as e:
            print(f"Autoencoder not loaded, using raw features: {e}")
            self.autoencoder = None
            self.autoencoder_loaded = False
            # We'll set state_dim when we first see the data

        # Initialize networks with placeholder input size
        # They will be reinitialized with correct size when we first see the data
        self.actor = None
        self.critic = None
        self.actor_optimizer = None
        self.critic_optimizer = None

        # Initialize reward calculator
        self.reward_calculator = RewardCalculator()

        # Training metrics
        self.metrics = {
            'actor_loss': [],
            'critic_loss': [],
            'entropy': [],
            'rewards': [],
            'portfolio_returns': [],
            'sharpe_ratios': []
        }

    def _initialize_networks(self, input_dim: int):
        """Initialize or reinitialize networks with the correct input dimension."""
        # If autoencoder is loaded, always use bottleneck_dim
        if self.autoencoder_loaded and self.autoencoder is not None:
            input_dim = self.autoencoder.bottleneck_dim
        if self.actor is None or self.actor.bottleneck_dim != input_dim:
            print(f"Initializing networks with input dimension: {input_dim}")
            self.actor = PolicyNetwork(bottleneck_dim=input_dim, n_instruments=self.n_instruments).to(self.device)
            self.critic = ValueNetwork(bottleneck_dim=input_dim).to(self.device)
            self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=self.actor_lr)
            self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=self.critic_lr)

    def encode_state(self, state: torch.Tensor) -> torch.Tensor:
        """
        Encode state using fusion autoencoder.
        
        Args:
            state: State tensor [batch_size, state_dim] or [state_dim]
            
        Returns:
            Encoded state
        """
        if not self.autoencoder_loaded or self.autoencoder is None:
            return state
        
        # Add batch dimension if needed
        single_state = False
        if state.dim() == 1:
            single_state = True
            state = state.unsqueeze(0)  # Add batch dimension
        
        # Encode state
        encoded_state = self.autoencoder.encode(state)
        
        # Remove batch dimension if input was a single state
        if single_state:
            encoded_state = encoded_state.squeeze(0)
            
        return encoded_state

    def get_action(self, state: torch.Tensor, training: bool = True) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get action from current state.
        Now returns raw position values that can be positive (long) or negative (short).
        
        Args:
            state: Current state tensor [batch_size, state_dim]
            training: Whether to use training mode
            
        Returns:
            action: Raw position values [batch_size, n_instruments] (can be positive or negative)
            log_prob: Log probability of the action
        """
        # Validate input
        if torch.isnan(state).any() or torch.isinf(state).any():
            print("Warning: NaN/Inf detected in state input. Replacing with zeros.")
            state = torch.nan_to_num(state, nan=0.0, posinf=0.0, neginf=0.0)
            
        # Always encode state if autoencoder is loaded
        if self.autoencoder_loaded and self.autoencoder is not None:
            state = self.encode_state(state)
            
        # Initialize networks if needed
        if self.actor is None:
            input_dim = state.shape[-1]
            self._initialize_networks(input_dim)
            self.state_dim = input_dim

        means = self.actor(state)
        
        # Validate means
        if torch.isnan(means).any() or torch.isinf(means).any():
            print("Warning: NaN/Inf detected in action means. Using zeros instead.")
            means = torch.zeros_like(means)
            
        action_dist = self.actor.get_action_distribution(means)
        if training:
            action = action_dist.rsample()
        else:
            action = action_dist.mean
            
        # Final validation of action
        if torch.isnan(action).any() or torch.isinf(action).any():
            print("Warning: NaN/Inf detected in sampled action. Using means instead.")
            action = torch.nan_to_num(means, nan=0.0, posinf=0.0, neginf=0.0)
            
        log_prob = action_dist.log_prob(action).sum(dim=-1)
        return action, log_prob
    
    def update_policy(self, 
                     states: torch.Tensor,
                     actions: torch.Tensor,
                     rewards: torch.Tensor,
                     next_states: torch.Tensor,
                     dones: torch.Tensor) -> Dict[str, float]:
        """
        Update policy using A2C algorithm with robust handling.
        """
        # Initialize networks if needed
        if self.actor is None:
            input_dim = states.shape[-1]
            self._initialize_networks(input_dim)
            self.state_dim = input_dim

        # Validate inputs
        if torch.isnan(states).any() or torch.isinf(states).any():
            print("Warning: NaN/Inf detected in states. Replacing with zeros.")
            states = torch.nan_to_num(states, nan=0.0, posinf=0.0, neginf=0.0)
        if torch.isnan(next_states).any() or torch.isinf(next_states).any():
            print("Warning: NaN/Inf detected in next_states. Replacing with zeros.")
            next_states = torch.nan_to_num(next_states, nan=0.0, posinf=0.0, neginf=0.0)
        if torch.isnan(rewards).any() or torch.isinf(rewards).any():
            print("Warning: NaN/Inf detected in rewards. Replacing with zeros.")
            rewards = torch.nan_to_num(rewards, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Clip rewards to prevent extreme values
        rewards = torch.clamp(rewards, -10.0, 10.0)

        # Encode states if autoencoder is available
        encoded_states = self.encode_state(states)
        encoded_next_states = self.encode_state(next_states)
        
        # Get value estimates
        values = self.critic(encoded_states)
        next_values = self.critic(encoded_next_states)
        
        # Calculate advantages with robust handling
        advantages = rewards + self.gamma * next_values * (1 - dones) - values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Get action distribution and log probabilities
        means = self.actor(encoded_states)
        action_dist = self.actor.get_action_distribution(means)
        log_probs = action_dist.log_prob(actions).sum(dim=-1)
        
 # Calculate entropy
        entropy = action_dist.entropy().mean()
        
        # Calculate losses with gradient clipping
        actor_loss = -(log_probs * advantages.detach()).mean() - self.entropy_weight * entropy
        critic_loss = advantages.pow(2).mean()
        
        # Update networks with gradient clipping
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=1.0)
        self.actor_optimizer.step()
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=1.0)
        self.critic_optimizer.step()
        
        # Update metrics
        self.metrics['actor_loss'].append(actor_loss.item())
        self.metrics['critic_loss'].append(critic_loss.item())
        self.metrics['entropy'].append(entropy.item())
        self.metrics['rewards'].append(rewards.mean().item())
        
        return {
            'actor_loss': actor_loss.item(),
            'critic_loss': critic_loss.item(),
            'entropy': entropy.item(),
            'mean_reward': rewards.mean().item()
        }
    
    def save_model(self, path: str):
        """Save model state."""
        torch.save({
            'actor_state_dict': self.actor.state_dict(),
            'critic_state_dict': self.critic.state_dict(),
            'actor_optimizer': self.actor_optimizer.state_dict(),
            'critic_optimizer': self.critic_optimizer.state_dict(),
            'metrics': self.metrics
        }, path)
    
    def load_model(self, path: str):
        """Load model state with robust compatibility handling."""
        try:
            # Try the standard loading first
            checkpoint = torch.load(path, map_location=self.device)
            
            # Check if networks are initialized
            if self.actor is None or self.critic is None:
                # Initialize networks if needed - try to extract the bottleneck_dim from checkpoint
                bottleneck_dim = None
                if 'actor_state_dict' in checkpoint:
                    # Try to find the first layer dimension
                    for key, param in checkpoint['actor_state_dict'].items():
                        if 'weight' in key and len(param.shape) == 2:
                            bottleneck_dim = param.shape[1]  # Input dimension
                            break
                
                # Use default if we couldn't determine
                if bottleneck_dim is None:
                    bottleneck_dim = 149  # Default
                    
                print(f"Initializing networks with bottleneck_dim={bottleneck_dim}")
                self._initialize_networks(bottleneck_dim)
            
            # Standard loading
            try:
                self.actor.load_state_dict(checkpoint['actor_state_dict'])
                self.critic.load_state_dict(checkpoint['critic_state_dict'])
                self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer'])
                self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer'])
                if 'metrics' in checkpoint:
                    self.metrics = checkpoint['metrics']
                print(f"Successfully loaded model from {path}")
                return
            except Exception as e:
                print(f"Standard loading failed: {e}. Trying compatibility module...")
            
            # If standard loading fails, use the compatibility module
            from rl.checkpoint_compat import fix_checkpoint_loading
            
            # Fix actor loading
            print("Attempting to fix actor network loading...")
            actor_success = fix_checkpoint_loading(self.actor, path, allow_partial=True)
            
            # Fix critic loading
            print("Attempting to fix critic network loading...")
            critic_success = fix_checkpoint_loading(self.critic, path, allow_partial=True)
            
            # Load optimizers if possible
            try:
                self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer'])
                self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer'])
                print("Successfully loaded optimizer states")
            except Exception as e:
                print(f"Warning: Could not load optimizer states: {e}")
                # Reinitialize optimizers
                self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.actor_lr)
                self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=self.critic_lr)
                
            # Load metrics if available
            if 'metrics' in checkpoint:
                self.metrics = checkpoint['metrics']
                
            print(f"Checkpoint loading completed with compatibility fixes")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            # Don't raise, just log - this allows execution to continue with fresh model

# Example usage
if __name__ == "__main__":
    # Create RL trader
    trader = RLTrader(
        actor_lr=1e-5, 
        critic_lr=1e-4, 
        entropy_weight=0.01
    )
    
    # Simulate market data
    batch_size = 4 # Smaller batch for update test
    n_features = trader.autoencoder.n_features
    n_instruments = len(PAIRS_BY_LIQUIDITY_OANDA)
    
    # Generate synthetic features for testing
    # Note: get_action expects raw features, not encoded state directly
    state_features_tensor = torch.randn(batch_size, n_features).to(trader.device)
    
    # Get action, log_prob, and encoded_state for a single step or a batch
    # For a batch, RL loop would typically collect these
    # Here we simulate getting it for the batch directly for testing update_policy
    action, log_prob = trader.get_action(state_features_tensor)
    
    print(f"Original State Features shape: {state_features_tensor.shape}")
    print(f"Sampled Action shape: {action.shape}")
    print(f"Log Prob shape: {log_prob.shape}")
    
    # Simulate price changes for reward calculation for the batch
    # Using the first action from the batch for reward demo if batch_size > 1
    # In a real loop, each action in the batch corresponds to a specific state and gets its own reward.
    price_changes = np.random.randn(n_instruments) * 0.01 
    
    # Calculate reward (example for the first item in batch)
    # In a real training loop, you'd calculate reward for each step in the batch.
    # The RewardCalculator state (mu, sigma_sq) would update per step.
    # For this test, we just call it once for one action.
    reward_info = trader.reward_calculator.calculate_reward(
        action[0].cpu().detach().numpy(), # Use a single action from the batch
        price_changes
    )
    print(f"\n--- Reward Calculation Example (for first action in batch) ---")
    print(f"Portfolio return: {reward_info['portfolio_return']:.6f}")
    print(f"Differential Sharpe: {reward_info['differential_sharpe']:.4f}")
    print(f"Final reward (raw): {reward_info['final_reward']:.4f}")
    print(f"Clipped reward: {reward_info['clipped_reward']:.4f}")

    # --- Test update_policy --- 
    print(f"\n--- Testing update_policy --- ")
    # Simulate a batch of experiences for update_policy
    # These would be collected from an environment interaction loop
    dummy_states = [torch.randn(1, n_features) for _ in range(batch_size)]
    dummy_actions = [torch.randn(1, n_instruments) for _ in range(batch_size)]
    dummy_rewards = [trader.reward_calculator.calculate_reward(np.random.randn(n_instruments), price_changes)['clipped_reward'] for _ in range(batch_size)]
    dummy_dones = [False for _ in range(batch_size)]
    if batch_size > 0:
        dummy_dones[-1] = True # Simulate one episode ending

    update_metrics = trader.update_policy(
        states=torch.cat(dummy_states, dim=0),
        actions=torch.cat(dummy_actions, dim=0),
        rewards=torch.tensor(dummy_rewards, dtype=torch.float32),
        next_states=torch.cat(dummy_states, dim=0),
        dones=torch.tensor(dummy_dones, dtype=torch.float32)
    )
    
    print("Update Policy Metrics:")
    for key, value in update_metrics.items():
        print(f"- {key}: {value:.6f}")
    
    # Save model (now A2C checkpoint)
    trader.save_model(os.path.join(MODELS_DIR, "rl_a2c_checkpoint.pt")) 
    
    # Example of loading the model
    print("\nAttempting to load the saved A2C model...")
    new_trader = RLTrader()
    new_trader.load_model(os.path.join(MODELS_DIR, "rl_a2c_checkpoint.pt"))
    print("Model loading test complete.") 