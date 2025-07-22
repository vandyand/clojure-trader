"""
Reward Calculator for Unified Futures RL Trading System

Implements the sophisticated reward mechanism as specified in reward-info.md:
1. Position normalization using Dirichlet concentration parameter
2. Entropy penalty for portfolio diversification
3. Differential Sharpe Ratio (DSR) calculation
4. Confidence weighting based on model confidence
5. Support for both long and short positions

This is the exact implementation from the existing codebase, adapted for futures trading.
"""

import numpy as np
from typing import Dict, Tuple
import logging

from constants import (
    CRYPTO_FUTURES_PAIRS, DSR_BETA, ENTROPY_SCALING, 
    CONFIDENCE_WEIGHTING, TRANSACTION_COST_RATE
)

logger = logging.getLogger(__name__)

class RewardCalculator:
    """
    Implements the reward mechanism as specified in reward-info.md
    Now supports both long and short positions for futures trading.
    """
    
    def __init__(self, n_instruments: int = 20, beta: float = DSR_BETA):
        self.n_instruments = n_instruments
        self.beta = beta
        
        # Initialize DSR tracking variables with more reasonable values
        self.mu_prev = 0.0  # Previous mean return
        self.sigma_sq_prev = 0.01  # Previous variance (0.1^2) - more reasonable initial value
        
        # Initialize tracking variables for Differential Sharpe Ratio
        self.mu = 0.0  # Mean return
        self.sigma_sq = 0.01  # Initial variance (0.1²) - more reasonable initial value
        
    def normalize_positions(self, raw_outputs: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Normalize positions using Dirichlet-inspired approach as in reward-info.md.
        
        Args:
            raw_outputs: Raw model outputs [n_instruments] (can be positive or negative)
            
        Returns:
            normalized_positions: Normalized positions [n_instruments]
            alpha_0: Total concentration parameter
        """
        # Calculate alpha values (position confidence)
        # Step 1: Split long/short positions
        long_positions = np.maximum(raw_outputs, 0)
        short_positions = np.maximum(-raw_outputs, 0)
        
        # Step 2: Calculate α values (confidence in each position)
        alpha = long_positions + short_positions
        
        # Step 3: Calculate total concentration parameter α₀
        alpha_0 = np.sum(alpha) + 1e-8  # Add epsilon for numerical stability
        
        # Step 4: Normalize positions by α₀, but scale up to maintain reasonable position sizes
        # Use a scaling factor to ensure positions are in a reasonable range (e.g., ±0.1 to ±0.5)
        scaling_factor = 5.0  # This will make positions roughly ±0.1 to ±0.5 instead of ±0.01
        normalized_positions = (alpha / alpha_0) * scaling_factor
        
        # Step 5: Restore signs (long positions positive, short positions negative)
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
        # Calculate normalized absolute positions
        abs_pos = np.abs(positions)
        p = abs_pos / (np.sum(abs_pos) + 1e-8)
        
        # Calculate entropy: H = -Σ p_i * ln(p_i)
        entropy = -np.sum(p * np.log(p + 1e-8))
        
        # Normalize entropy by log(n_instruments)
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
        # But add a minimum scaling factor to prevent positions from becoming too small
        scaling_factor = max(0.1, 1.0 - normalized_entropy)
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
            logger.warning("NaN/Inf detected in return. Replacing with zero.")
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
        
        # Handle NaN/Inf and clip extreme values
        if np.isnan(dsr) or np.isinf(dsr):
            return 0.0
        
        # Clip DSR to reasonable bounds (-10 to 10) to prevent extreme values
        dsr = np.clip(dsr, -10.0, 10.0)
            
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
    
    def calculate_transaction_costs(self, current_positions: np.ndarray, 
                                  previous_positions: np.ndarray) -> float:
        """
        Calculate transaction costs for position changes.
        
        Args:
            current_positions: Current position sizes [n_instruments]
            previous_positions: Previous position sizes [n_instruments]
            
        Returns:
            Total transaction cost
        """
        # Calculate position changes
        position_changes = np.abs(current_positions - previous_positions)
        
        # Apply transaction cost rate
        transaction_costs = TRANSACTION_COST_RATE * position_changes
        
        return np.sum(transaction_costs)
    
    def calculate_reward(self, 
                        raw_outputs: np.ndarray, 
                        price_changes: np.ndarray,
                        previous_positions: np.ndarray = None) -> Dict:
        """
        Complete reward calculation pipeline as specified in reward-info.md.
        
        Args:
            raw_outputs: Model outputs for position sizing [n_instruments]
            price_changes: Percentage price changes for instruments [n_instruments]
            previous_positions: Previous position sizes for transaction cost calculation
            
        Returns:
            Dictionary containing all intermediate calculations and final reward
        """
        # Step 1: Normalize positions using Dirichlet-inspired approach
        positions, alpha_0 = self.normalize_positions(raw_outputs)
        
        # Step 2: Calculate entropy penalty
        entropy, norm_entropy = self.position_entropy(positions)
        final_positions, scaling = self.apply_entropy_penalty(positions, norm_entropy)
        
        # Step 3: Calculate portfolio return
        R_t = self.portfolio_return(final_positions, price_changes)
        
        # Step 4: Calculate transaction costs if previous positions provided
        transaction_cost = 0.0
        if previous_positions is not None:
            transaction_cost = self.calculate_transaction_costs(final_positions, previous_positions)
            R_t -= transaction_cost  # Subtract transaction costs from return
        
        # Step 5: Calculate reward using simplified approach
        # Use portfolio return directly with risk penalty
        risk_penalty = 0.1 * np.std(price_changes)  # Simple risk penalty
        reward = R_t - risk_penalty
        
        # Step 6: Apply confidence weighting
        confidence = 1.0 - 1.0 / (alpha_0 + 1.0)
        reward = reward * confidence
        
        # Step 7: Clip reward to prevent extreme values
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
            'transaction_cost': transaction_cost,
            'risk_penalty': risk_penalty,
            'differential_sharpe': reward,  # Keep for compatibility
            'actual_sharpe': self._calculate_actual_sharpe(R_t),  # Add actual Sharpe ratio
            'confidence_weight': confidence,
            'final_reward': reward,
            'clipped_reward': clipped_reward,
            'mu_prev': self.mu_prev,
            'sigma_sq_prev': self.sigma_sq_prev
        }
    
    def reset_state(self):
        """Reset the DSR tracking state."""
        self.mu_prev = 0.0
        self.sigma_sq_prev = 0.0001
        self.mu = 0.0
        self.sigma_sq = 0.0001
    
    def get_state(self) -> Dict:
        """Get current state for checkpointing."""
        return {
            'mu_prev': self.mu_prev,
            'sigma_sq_prev': self.sigma_sq_prev,
            'mu': self.mu,
            'sigma_sq': self.sigma_sq
        }
    
    def set_state(self, state: Dict):
        """Set state from checkpoint."""
        self.mu_prev = state.get('mu_prev', 0.0)
        self.sigma_sq_prev = state.get('sigma_sq_prev', 0.0001)
        self.mu = state.get('mu', 0.0)
        self.sigma_sq = state.get('sigma_sq', 0.0001)
    
    def _calculate_actual_sharpe(self, R_t: float) -> float:
        """
        Calculate the actual Sharpe ratio using rolling mean and variance.
        
        Args:
            R_t: Current portfolio return
            
        Returns:
            Sharpe ratio (return / volatility)
        """
        # Update rolling statistics
        self.mu = self.mu + self.beta * (R_t - self.mu)
        self.sigma_sq = self.sigma_sq + self.beta * (R_t ** 2 - self.sigma_sq)
        
        # Calculate Sharpe ratio
        volatility = np.sqrt(max(self.sigma_sq, 1e-8))  # Avoid division by zero
        
        if volatility < 1e-8:
            return 0.0
        
        sharpe = self.mu / volatility
        
        # Handle NaN/Inf
        if np.isnan(sharpe) or np.isinf(sharpe):
            return 0.0
        
        return float(sharpe) 