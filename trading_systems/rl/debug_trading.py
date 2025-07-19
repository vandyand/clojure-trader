#!/usr/bin/env python
"""
Diagnostic script for troubleshooting the trading system.
This runs a short training session with extensive logging to identify issues.
"""
import os
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
import pandas as pd

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.policy_network import RLTrader, RewardCalculator
from rl.trading_system import TradingSystem
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"trading_system_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradingDiagnostics")

def patch_trading_system():
    """
    Patch the TradingSystem class with diagnostic logging.
    """
    # Store original methods
    original_evaluate = TradingSystem.evaluate
    original_load_market_data = TradingSystem._load_market_data
    
    def patched_evaluate(self, test_data=None, n_episodes=100, episode_length=1000):
        """
        Patched evaluate method with additional logging.
        """
        logger.info("Starting enhanced diagnostic evaluation")
        
        if test_data is None:
            test_data = self._load_market_data()
        
        # Log data shape information
        logger.info(f"Test data shape: features={test_data['features'].shape}, price_changes={test_data['price_changes'].shape}")
        
        # Check for NaN/Inf values
        logger.info(f"Features contain NaN: {np.isnan(test_data['features']).any()}")
        logger.info(f"Features contain Inf: {np.isinf(test_data['features']).any()}")
        logger.info(f"Price changes contain NaN: {np.isnan(test_data['price_changes']).any()}")
        logger.info(f"Price changes contain Inf: {np.isinf(test_data['price_changes']).any()}")
        
        # Log price changes statistics
        price_changes_flat = test_data['price_changes'].flatten()
        logger.info(f"Price changes stats: min={np.min(price_changes_flat):.6f}, max={np.max(price_changes_flat):.6f}, mean={np.mean(price_changes_flat):.6f}, std={np.std(price_changes_flat):.6f}")
        logger.info(f"Non-zero price changes: {np.count_nonzero(price_changes_flat)}/{len(price_changes_flat)} ({np.count_nonzero(price_changes_flat)/len(price_changes_flat)*100:.2f}%)")
        
        # Initialize evaluation metrics
        episode_returns = []
        episode_sharpes = []
        episode_drawdowns = []
        episode_win_rates = []
        episode_avg_trade_returns = []
        all_positions = []
        all_actions_raw = []  # Store raw actions
        
        # Make sure we track missing instruments
        if 'missing_instruments' in test_data:
            self.missing_instruments = test_data['missing_instruments']
            logger.info(f"Missing instruments: {len(self.missing_instruments)}/{len(PAIRS_BY_LIQUIDITY_OANDA)}")
            if self.missing_instruments:
                logger.info(f"Missing instrument list: {self.missing_instruments}")
        
        max_start_idx = max(0, len(test_data['features']) - episode_length - 1)
        
        # Evaluation loop
        for episode in range(n_episodes):
            # Random starting point
            start_idx = np.random.randint(0, max_start_idx) if max_start_idx > 0 else 0
            end_idx = min(start_idx + episode_length, len(test_data['features']) - 1)
            
            # Reset reward calculator
            self.previous_positions = torch.zeros(len(PAIRS_BY_LIQUIDITY_OANDA))
            
            # Episode data
            episode_states = test_data['features'][start_idx:end_idx]
            episode_price_changes = test_data['price_changes'][start_idx:end_idx]
            
            # Episode metrics
            episode_returns_list = []
            positions = []
            raw_actions_list = []
            
            # Run episode
            for i in range(len(episode_states)):
                # Get current state
                state = torch.tensor(episode_states[i], dtype=torch.float32)
                
                # Get action (use mean for evaluation)
                action, _ = self.trader.get_action(state, training=False)
                
                # Log action statistics
                action_np = action.detach().numpy()
                raw_actions_list.append(action_np.copy())
                
                if i % 100 == 0 or i == 0:  # Log only occasionally to avoid flooding
                    logger.info(f"Episode {episode+1}, Step {i}: Raw action stats: min={action_np.min():.4f}, max={action_np.max():.4f}, mean={action_np.mean():.4f}")
                    logger.info(f"Episode {episode+1}, Step {i}: Non-zero positions: {np.count_nonzero(action_np)}/{len(action_np)}")
                
                # Calculate reward
                price_change = torch.tensor(episode_price_changes[i], dtype=torch.float32)
                reward_info = self.reward_calculator.calculate_reward(
                    action.detach().numpy(),
                    episode_price_changes[i]
                )
                
                # Log additional reward details occasionally
                if i % 100 == 0 or i == 0:
                    logger.info(f"Episode {episode+1}, Step {i}: Reward calculation:")
                    logger.info(f"  - Raw outputs: min={np.min(action_np):.4f}, max={np.max(action_np):.4f}")
                    logger.info(f"  - Normalized positions: min={np.min(reward_info['positions']):.4f}, max={np.max(reward_info['positions']):.4f}")
                    logger.info(f"  - Final positions: min={np.min(reward_info['final_positions']):.4f}, max={np.max(reward_info['final_positions']):.4f}")
                    logger.info(f"  - Position entropy: {reward_info['position_entropy']:.4f}")
                    logger.info(f"  - Portfolio return: {reward_info['portfolio_return']:.4f}")
                    logger.info(f"  - DSR: {reward_info['differential_sharpe']:.4f}")
                    logger.info(f"  - Final reward: {reward_info['final_reward']:.4f}")
                
                # Update positions for transaction cost calculation
                portfolio_return = reward_info['portfolio_return']
                
                # Store results
                episode_returns_list.append(portfolio_return)
                positions.append(reward_info['final_positions'])
            
            # Add raw actions for this episode
            all_actions_raw.extend(raw_actions_list)
            
            # Calculate episode metrics
            episode_return = np.sum(episode_returns_list)
            episode_returns.append(episode_return)
            
            # Calculate Sharpe ratio
            if len(episode_returns_list) > 1 and np.std(episode_returns_list) > 0:
                sharpe = np.mean(episode_returns_list) / np.std(episode_returns_list) * np.sqrt(252)
            else:
                sharpe = 0
            episode_sharpes.append(sharpe)
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown(np.array(episode_returns_list))
            episode_drawdowns.append(max_drawdown)
            
            # Calculate win rate
            win_rate = np.mean(np.array(episode_returns_list) > 0) if episode_returns_list else 0
            episode_win_rates.append(win_rate)
            
            # Calculate average trade return
            avg_trade_return = np.mean(episode_returns_list) if episode_returns_list else 0
            episode_avg_trade_returns.append(avg_trade_return)
            
            # Store positions
            all_positions.extend(positions)
            
            # Log episode summary
            logger.info(f"Episode {episode+1} Summary:")
            logger.info(f"  - Return: {episode_return:.6f}")
            logger.info(f"  - Sharpe: {sharpe:.6f}")
            logger.info(f"  - Max Drawdown: {max_drawdown:.6f}")
            logger.info(f"  - Win Rate: {win_rate:.6f}")
            logger.info(f"  - Avg Trade Return: {avg_trade_return:.6f}")
            
            # Print progress
            print(f"\rEvaluating episode {episode+1}/{n_episodes}: Return={episode_return:.6f}, Sharpe={sharpe:.6f}, MaxDD={max_drawdown:.6f}, WinRate={win_rate:.6f}", end="")
        
        print("\n")
        
        # Additional diagnostic information
        all_positions_np = np.array(all_positions)
        all_actions_raw_np = np.array(all_actions_raw)
        
        logger.info("Final Diagnostics Summary:")
        logger.info(f"Raw Actions - min: {all_actions_raw_np.min():.6f}, max: {all_actions_raw_np.max():.6f}, mean: {all_actions_raw_np.mean():.6f}, non-zero: {np.count_nonzero(all_actions_raw_np)/all_actions_raw_np.size*100:.2f}%")
        logger.info(f"Final Positions - min: {all_positions_np.min():.6f}, max: {all_positions_np.max():.6f}, mean: {all_positions_np.mean():.6f}, non-zero: {np.count_nonzero(all_positions_np)/all_positions_np.size*100:.2f}%")
        
        # Check for zero positions
        zero_positions = np.all(np.abs(all_positions_np) < 1e-6)
        logger.info(f"All positions effectively zero: {zero_positions}")
        
        # Save raw actions and positions for inspection
        np.save("diagnostic_raw_actions.npy", all_actions_raw_np)
        np.save("diagnostic_positions.npy", all_positions_np)
        
        # Calculate overall metrics
        results = {
            'total_return': np.mean(episode_returns),
            'sharpe_ratio': np.mean(episode_sharpes),
            'max_drawdown': np.mean(episode_drawdowns),
            'win_rate': np.mean(episode_win_rates),
            'avg_trade_return': np.mean(episode_avg_trade_returns),
            'positions': np.array(all_positions),
            'raw_actions': np.array(all_actions_raw)
        }
        
        logger.info(f"Overall Results:")
        logger.info(f"  - Total Return: {results['total_return']:.6f}")
        logger.info(f"  - Sharpe Ratio: {results['sharpe_ratio']:.6f}")
        logger.info(f"  - Max Drawdown: {results['max_drawdown']:.6f}")
        logger.info(f"  - Win Rate: {results['win_rate']:.6f}")
        logger.info(f"  - Avg Trade Return: {results['avg_trade_return']:.6f}")
        
        return results
    
    def patched_load_market_data(self):
        """
        Patched market data loading with additional diagnostic information.
        """
        logger.info("Loading market data with enhanced diagnostics")
        
        result = original_load_market_data(self)
        
        logger.info(f"Loaded features shape: {result['features'].shape}")
        logger.info(f"Loaded price changes shape: {result['price_changes'].shape}")
        
        # Check for missing instruments
        missing_price_features = result.get('missing_instruments', [])
        logger.info(f"Total missing instruments: {len(missing_price_features)}/{len(PAIRS_BY_LIQUIDITY_OANDA)}")
        if missing_price_features:
            logger.info(f"Missing instruments: {missing_price_features}")
        
        # Check data quality
        features = result['features']
        price_changes = result['price_changes']
        
        logger.info(f"Features stats: min={np.min(features):.6f}, max={np.max(features):.6f}, mean={np.mean(features):.6f}")
        logger.info(f"Features contain NaN: {np.isnan(features).any()}")
        logger.info(f"Features contain Inf: {np.isinf(features).any()}")
        
        logger.info(f"Price changes stats: min={np.min(price_changes):.6f}, max={np.max(price_changes):.6f}, mean={np.mean(price_changes):.6f}")
        logger.info(f"Price changes contain NaN: {np.isnan(price_changes).any()}")
        logger.info(f"Price changes contain Inf: {np.isinf(price_changes).any()}")
        
        # Check how many price changes are zero
        zero_changes = np.sum(np.abs(price_changes) < 1e-10)
        logger.info(f"Zero price changes: {zero_changes}/{price_changes.size} ({zero_changes/price_changes.size*100:.2f}%)")
        
        return result
    
    # Apply the patches
    TradingSystem.evaluate = patched_evaluate
    TradingSystem._load_market_data = patched_load_market_data
    
    logger.info("Trading system methods patched with diagnostic enhancements")
    
    # Also patch RLTrader.update_policy to monitor gradients
    original_update_policy = RLTrader.update_policy
    
    def patched_update_policy(self, states, actions, rewards, next_states, dones):
        """
        Patched update_policy method with gradient monitoring.
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
        
        # Log advantage statistics
        logger.info(f"Advantages stats: min={advantages.min().item():.6f}, max={advantages.max().item():.6f}, mean={advantages.mean().item():.6f}, std={advantages.std().item():.6f}")
        
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
        
        # Update networks with gradient monitoring
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        actor_grad_norm = torch.nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=1.0)
        self.actor_optimizer.step()
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        critic_grad_norm = torch.nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=1.0)
        self.critic_optimizer.step()
        
        # Log gradient norms
        logger.info(f"Gradient norms - Actor: {actor_grad_norm:.6f}, Critic: {critic_grad_norm:.6f}")
        
        # Update metrics
        self.metrics['actor_loss'].append(actor_loss.item())
        self.metrics['critic_loss'].append(critic_loss.item())
        self.metrics['entropy'].append(entropy.item())
        self.metrics['rewards'].append(rewards.mean().item())
        
        return {
            'actor_loss': actor_loss.item(),
            'critic_loss': critic_loss.item(),
            'entropy': entropy.item(),
            'mean_reward': rewards.mean().item(),
            'actor_grad_norm': actor_grad_norm.item(),
            'critic_grad_norm': critic_grad_norm.item()
        }
    
    # Apply the patch
    RLTrader.update_policy = patched_update_policy
    
    logger.info("RLTrader.update_policy patched with gradient monitoring")
    
    return logger.info("All diagnostic patches applied successfully")


def test_fixed_positions():
    """
    Test if evaluation pipeline works with simple fixed positions.
    This will help determine if the issue is with position generation or reward calculation.
    """
    logger.info("Starting fixed position test")
    
    system = TradingSystem()
    test_data = system._load_market_data()
    
    # Store original methods
    original_get_action = system.trader.get_action
    
    # Custom action function that returns fixed positions
    def fixed_action(*args, **kwargs):
        # Generate alternating long/short positions
        action = torch.zeros(len(PAIRS_BY_LIQUIDITY_OANDA))
        action[0::2] = 0.1  # Long on even instruments
        action[1::2] = -0.1  # Short on odd instruments
        return action, None
    
    logger.info("Using fixed actions: alternating +0.1/-0.1 positions")
    
    # Override the get_action method
    system.trader.get_action = fixed_action
    
    # Evaluate with fixed actions
    results = system.evaluate(test_data, n_episodes=5, episode_length=100)
    
    # Restore original function
    system.trader.get_action = original_get_action
    
    logger.info("Fixed position test results:")
    logger.info(f"Total Return: {results['total_return']:.6f}")
    logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.6f}")
    logger.info(f"Max Drawdown: {results['max_drawdown']:.6f}")
    
    return results


def analyze_reward_calculator():
    """
    Analyze the reward calculator with synthetic data to verify its functionality.
    """
    logger.info("Analyzing reward calculator with synthetic data")
    
    # Create a reward calculator
    calculator = RewardCalculator()
    
    # Generate synthetic price changes - some positive, some negative
    price_changes = np.zeros(20)
    price_changes[0:10] = 0.01  # 1% increase
    price_changes[10:20] = -0.01  # 1% decrease
    
    logger.info(f"Synthetic price changes: {price_changes}")
    
    # Test cases with different position patterns
    test_cases = [
        ("All zeros", np.zeros(20)),
        ("All small positive", np.ones(20) * 0.1),
        ("All small negative", np.ones(20) * -0.1),
        ("Mixed positions", np.array([0.1 if i % 2 == 0 else -0.1 for i in range(20)])),
        ("Single large position", np.array([1.0 if i == 0 else 0.0 for i in range(20)])),
        ("Alternating extreme", np.array([10.0 if i % 2 == 0 else -10.0 for i in range(20)]))
    ]
    
    for name, positions in test_cases:
        logger.info(f"\nTesting case: {name}")
        
        # Calculate reward
        result = calculator.calculate_reward(positions, price_changes)
        
        # Log detailed results
        logger.info(f"Raw positions: min={positions.min():.6f}, max={positions.max():.6f}, mean={positions.mean():.6f}")
        logger.info(f"Normalized positions: min={result['positions'].min():.6f}, max={result['positions'].max():.6f}, mean={result['positions'].mean():.6f}")
        logger.info(f"Final positions: min={result['final_positions'].min():.6f}, max={result['final_positions'].max():.6f}, mean={result['final_positions'].mean():.6f}")
        logger.info(f"Position entropy: {result['position_entropy']:.6f}")
        logger.info(f"Normalized entropy: {result['normalized_entropy']:.6f}")
        logger.info(f"Scaling factor: {result['scaling_factor']:.6f}")
        logger.info(f"Portfolio return: {result['portfolio_return']:.6f}")
        logger.info(f"Differential sharpe: {result['differential_sharpe']:.6f}")
        logger.info(f"Final reward: {result['final_reward']:.6f}")
    
    logger.info("Reward calculator analysis complete")


def run_training_diagnostics():
    """
    Run a short training session with diagnostics to identify issues.
    """
    logger.info("Starting training diagnostics")
    
    # Create trading system
    system = TradingSystem()
    
    # Get market data
    market_data = system._load_market_data()
    
    # Run a short training session
    n_epochs = 5
    batch_size = 32
    
    logger.info(f"Running {n_epochs} training epochs with batch size {batch_size}")
    
    for epoch in range(n_epochs):
        logger.info(f"\n=== Epoch {epoch+1}/{n_epochs} ===")
        
        epoch_metrics = system._train_epoch(market_data, batch_size)
        
        # Log epoch metrics
        logger.info(f"Epoch {epoch+1} metrics:")
        logger.info(f"Average Reward: {epoch_metrics['reward']:.6f}")
        logger.info(f"Average Loss: {epoch_metrics['loss']:.6f}")
        logger.info(f"Portfolio Return: {epoch_metrics['return']:.6f}")
        logger.info(f"DSR: {epoch_metrics['dsr']:.6f}")
    
    # Run evaluation after training
    logger.info("\n=== Evaluation after training ===")
    eval_results = system.evaluate(market_data, n_episodes=5, episode_length=100)
    
    logger.info("Training diagnostics complete")


if __name__ == "__main__":
    logger.info("========== STARTING TRADING SYSTEM DIAGNOSTICS ==========")
    
    # Apply diagnostic patches
    patch_trading_system()
    
    # Analyze reward calculator
    analyze_reward_calculator()
    
    # Test with fixed positions
    fixed_position_results = test_fixed_positions()
    
    # Run training diagnostics
    run_training_diagnostics()
    
    logger.info("========== TRADING SYSTEM DIAGNOSTICS COMPLETE ==========") 