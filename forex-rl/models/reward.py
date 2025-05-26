# models/reward.py
import torch
import numpy as np
from typing import Dict, Tuple, Optional, Any
import logging
from config.settings import config

logger = logging.getLogger(__name__)

class ForexRewardFunction:
    """
    Comprehensive reward function for Forex RL trading
    
    Implements the complete pipeline from raw model outputs to reward calculation:
    1. Position confidence calculation (Dirichlet-inspired)
    2. Position normalization
    3. Entropy penalty for diversification
    4. Portfolio return calculation
    5. Differential Sharpe Ratio (DSR)
    6. Confidence weighting
    
    Based on the specification in reward-info.md
    """
    
    def __init__(self, 
                 beta: float = 0.95,
                 initial_mu: float = 0.0,
                 initial_sigma_sq: float = 0.0001,
                 reward_clipping: Tuple[float, float] = (-10.0, 10.0),
                 entropy_penalty: bool = True,
                 confidence_weighting: bool = True,
                 device: str = 'cpu'):
        """
        Initialize the reward function
        
        Args:
            beta: DSR decay rate (0.95 default)
            initial_mu: Initial mean return
            initial_sigma_sq: Initial return variance
            reward_clipping: Min/max reward values
            entropy_penalty: Whether to apply entropy penalty
            confidence_weighting: Whether to apply confidence weighting
            device: Device for tensor operations
        """
        self.beta = beta
        self.initial_mu = initial_mu
        self.initial_sigma_sq = initial_sigma_sq
        self.reward_clipping = reward_clipping
        self.entropy_penalty = entropy_penalty
        self.confidence_weighting = confidence_weighting
        self.device = torch.device(device)
        
        # State tracking for DSR
        self.reset_state()
        
        logger.info(f"Initialized ForexRewardFunction: beta={beta}, entropy_penalty={entropy_penalty}, confidence_weighting={confidence_weighting}")
    
    def reset_state(self):
        """Reset the internal state (mean and variance tracking)"""
        self.mu = self.initial_mu
        self.sigma_sq = self.initial_sigma_sq
        logger.debug("Reset reward function state")
    
    def calculate_alpha(self, raw_outputs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Calculate position confidence (alpha) values from raw model outputs
        
        Args:
            raw_outputs: Raw model outputs for position sizing [batch_size, n_instruments]
            
        Returns:
            alpha: Position confidence values [batch_size, n_instruments]
            alpha_0: Total concentration parameter [batch_size]
        """
        # Split into long and short components
        long = torch.clamp(raw_outputs, min=0.0)
        short = torch.clamp(-raw_outputs, min=0.0)
        
        # Alpha represents confidence in each position
        alpha = long + short
        
        # Total concentration parameter
        alpha_0 = torch.sum(alpha, dim=-1)
        
        return alpha, alpha_0
    
    def normalize_positions(self, alpha: torch.Tensor, alpha_0: torch.Tensor) -> torch.Tensor:
        """
        Normalize positions using total concentration parameter
        
        Args:
            alpha: Position confidence values [batch_size, n_instruments]
            alpha_0: Total concentration parameter [batch_size]
            
        Returns:
            Normalized positions [batch_size, n_instruments]
        """
        # Prevent division by zero
        alpha_0_safe = alpha_0 + 1e-8
        
        # Normalize positions to sum to 1
        positions = alpha / alpha_0_safe.unsqueeze(-1)
        
        return positions
    
    def position_entropy(self, positions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Calculate position entropy and normalized entropy
        
        Args:
            positions: Position weights [batch_size, n_instruments]
            
        Returns:
            entropy: Raw entropy values [batch_size]
            normalized_entropy: Normalized entropy (0-1) [batch_size]
        """
        # Get absolute positions for entropy calculation
        abs_pos = torch.abs(positions)
        
        # Normalize to probabilities
        pos_sum = torch.sum(abs_pos, dim=-1, keepdim=True) + 1e-8
        p = abs_pos / pos_sum
        
        # Calculate entropy: H = -sum(p * log(p))
        log_p = torch.log(p + 1e-8)  # Add epsilon for numerical stability
        entropy = -torch.sum(p * log_p, dim=-1)
        
        # Normalize by maximum possible entropy (log(n))
        n_instruments = positions.shape[-1]
        max_entropy = np.log(n_instruments) if n_instruments > 1 else 1.0
        normalized_entropy = entropy / max_entropy
        
        return entropy, normalized_entropy
    
    def apply_entropy_penalty(self, positions: torch.Tensor, normalized_entropy: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply entropy-based scaling to positions
        
        Args:
            positions: Position weights [batch_size, n_instruments]
            normalized_entropy: Normalized entropy [batch_size]
            
        Returns:
            final_positions: Scaled positions [batch_size, n_instruments]
            scaling_factor: Applied scaling factor [batch_size]
        """
        if not self.entropy_penalty:
            return positions, torch.ones_like(normalized_entropy)
        
        # Scaling factor: 1 - normalized_entropy
        # High entropy (diversified) -> low scaling (smaller positions)
        # Low entropy (concentrated) -> high scaling (larger positions)
        scaling_factor = 1.0 - normalized_entropy
        
        # Apply scaling
        final_positions = positions * scaling_factor.unsqueeze(-1)
        
        return final_positions, scaling_factor
    
    def portfolio_return(self, final_positions: torch.Tensor, price_changes: torch.Tensor) -> torch.Tensor:
        """
        Calculate portfolio return from positions and price changes
        
        Args:
            final_positions: Final position weights [batch_size, n_instruments]
            price_changes: Price changes for each instrument [batch_size, n_instruments]
            
        Returns:
            Portfolio return [batch_size]
        """
        # Portfolio return = sum(position_i * price_change_i)
        portfolio_return = torch.sum(final_positions * price_changes, dim=-1)
        
        return portfolio_return
    
    def differential_sharpe_ratio(self, R_t: torch.Tensor) -> Tuple[torch.Tensor, float, float]:
        """
        Calculate differential Sharpe ratio with exponential moving averages
        
        Args:
            R_t: Portfolio return [batch_size] or scalar
            
        Returns:
            dsr: Differential Sharpe ratio [batch_size] or scalar
            mu_t: Updated mean return
            sigma_sq_t: Updated return variance
        """
        # Handle both batch and single returns
        if isinstance(R_t, torch.Tensor):
            R_t_mean = R_t.mean().item()  # Use mean for state update
        else:
            R_t_mean = R_t
        
        # Calculate delta
        delta = R_t_mean - self.mu
        
        # Update mean and variance using exponential moving average
        mu_t = self.mu + self.beta * delta
        sigma_sq_t = self.sigma_sq + self.beta * (R_t_mean**2 - self.sigma_sq)
        
        # Calculate DSR
        numerator = self.beta * delta - 0.5 * (self.beta**2) * self.sigma_sq
        denominator = (self.sigma_sq + self.beta * delta**2)**1.5 + 1e-12
        
        if isinstance(R_t, torch.Tensor):
            # For batch processing, use current state for all samples
            delta_batch = R_t - self.mu
            numerator_batch = self.beta * delta_batch - 0.5 * (self.beta**2) * self.sigma_sq
            denominator_batch = (self.sigma_sq + self.beta * delta_batch**2)**1.5 + 1e-12
            dsr = numerator_batch / denominator_batch
        else:
            dsr = numerator / denominator
        
        # Update internal state
        self.mu = mu_t
        self.sigma_sq = sigma_sq_t
        
        return dsr, mu_t, sigma_sq_t
    
    def confidence_weighted_reward(self, dsr: torch.Tensor, alpha_0: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply confidence weighting based on Dirichlet concentration
        
        Args:
            dsr: Differential Sharpe ratio [batch_size]
            alpha_0: Total concentration parameter [batch_size]
            
        Returns:
            weighted_reward: Confidence-weighted reward [batch_size]
            confidence: Confidence weight [batch_size]
        """
        if not self.confidence_weighting:
            return dsr, torch.ones_like(alpha_0)
        
        # Confidence weight: 1 - 1/(alpha_0 + 1)
        # High alpha_0 (confident) -> high weight
        # Low alpha_0 (uncertain) -> low weight
        confidence = 1.0 - 1.0 / (alpha_0 + 1.0)
        
        # Apply confidence weighting
        weighted_reward = dsr * confidence
        
        return weighted_reward, confidence
    
    def forward(self, 
                raw_outputs: torch.Tensor, 
                price_changes: torch.Tensor,
                return_details: bool = False) -> torch.Tensor:
        """
        Complete reward calculation pipeline
        
        Args:
            raw_outputs: Raw model outputs [batch_size, n_instruments]
            price_changes: Price changes [batch_size, n_instruments]
            return_details: Whether to return detailed intermediate results
            
        Returns:
            reward: Final reward values [batch_size]
            details: (Optional) Dictionary with intermediate calculations
        """
        # Ensure tensors are on correct device
        raw_outputs = raw_outputs.to(self.device)
        price_changes = price_changes.to(self.device)
        
        # 1. Calculate position confidence parameters
        alpha, alpha_0 = self.calculate_alpha(raw_outputs)
        
        # 2. Normalize positions
        positions = self.normalize_positions(alpha, alpha_0)
        
        # 3. Calculate entropy penalty
        entropy, norm_entropy = self.position_entropy(positions)
        final_positions, scaling = self.apply_entropy_penalty(positions, norm_entropy)
        
        # 4. Calculate portfolio return
        R_t = self.portfolio_return(final_positions, price_changes)
        
        # 5. Update differential Sharpe ratio
        dsr, mu_t, sigma_sq_t = self.differential_sharpe_ratio(R_t)
        
        # 6. Calculate confidence-weighted reward
        reward, confidence = self.confidence_weighted_reward(dsr, alpha_0)
        
        # 7. Apply reward clipping
        if self.reward_clipping:
            reward = torch.clamp(reward, min=self.reward_clipping[0], max=self.reward_clipping[1])
        
        if return_details:
            details = {
                'raw_outputs': raw_outputs,
                'alpha': alpha,
                'alpha_0': alpha_0,
                'normalized_positions': positions,
                'position_entropy': entropy,
                'normalized_entropy': norm_entropy,
                'scaling_factor': scaling,
                'final_positions': final_positions,
                'portfolio_return': R_t,
                'differential_sharpe': dsr,
                'updated_mean': mu_t,
                'updated_variance': sigma_sq_t,
                'confidence_weight': confidence,
                'final_reward': reward
            }
            return reward, details
        
        return reward
    
    def __call__(self, raw_outputs: torch.Tensor, price_changes: torch.Tensor, **kwargs) -> torch.Tensor:
        """Make the class callable"""
        return self.forward(raw_outputs, price_changes, **kwargs)
    
    def get_state(self) -> Dict[str, float]:
        """Get current state for checkpointing"""
        return {
            'mu': self.mu,
            'sigma_sq': self.sigma_sq,
            'beta': self.beta
        }
    
    def set_state(self, state: Dict[str, float]):
        """Set state from checkpoint"""
        self.mu = state['mu']
        self.sigma_sq = state['sigma_sq']
        self.beta = state.get('beta', self.beta)
        logger.info(f"Restored reward function state: mu={self.mu:.6f}, sigma_sq={self.sigma_sq:.6f}")


def create_reward_function(**kwargs) -> ForexRewardFunction:
    """
    Factory function to create reward function with config defaults
    
    Args:
        **kwargs: Override configuration parameters
        
    Returns:
        Initialized ForexRewardFunction
    """
    # Get defaults from config
    reward_config = config.reward
    
    # Override with provided kwargs
    params = {
        'beta': reward_config.beta,
        'reward_clipping': reward_config.reward_clipping,
        'entropy_penalty': reward_config.entropy_penalty,
        'confidence_weighting': reward_config.confidence_weighting,
        **kwargs
    }
    
    return ForexRewardFunction(**params)


def test_reward_function():
    """Test the reward function with sample data"""
    logger.info("Testing reward function...")
    
    # Create reward function
    reward_fn = ForexRewardFunction()
    
    # Sample data (batch_size=2, n_instruments=3)
    raw_outputs = torch.tensor([
        [0.8, -0.4, -0.2],  # Sample 1
        [0.5, 0.3, -0.1]    # Sample 2
    ], dtype=torch.float32)
    
    price_changes = torch.tensor([
        [0.005, -0.003, 0.008],  # +0.5%, -0.3%, +0.8%
        [0.002, 0.001, -0.004]   # +0.2%, +0.1%, -0.4%
    ], dtype=torch.float32)
    
    # Test forward pass
    reward, details = reward_fn(raw_outputs, price_changes, return_details=True)
    
    # Validate shapes
    assert reward.shape == (2,), f"Expected reward shape (2,), got {reward.shape}"
    assert details['final_positions'].shape == (2, 3), f"Expected positions shape (2, 3), got {details['final_positions'].shape}"
    
    logger.info(f"✓ Reward function test passed!")
    logger.info(f"  Sample rewards: {reward.tolist()}")
    logger.info(f"  Final positions: {details['final_positions'].tolist()}")
    logger.info(f"  Portfolio returns: {details['portfolio_return'].tolist()}")
    logger.info(f"  Confidence weights: {details['confidence_weight'].tolist()}")
    
    # Test state management
    state = reward_fn.get_state()
    logger.info(f"  Final state: mu={state['mu']:.6f}, sigma_sq={state['sigma_sq']:.6f}")
    
    return True


if __name__ == "__main__":
    # Run tests
    test_reward_function() 