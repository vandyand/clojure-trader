#!/usr/bin/env python3
"""
Integration test for all model components
Tests networks, agents, and reward function working together
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import torch
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from models import (
    ForexRLNetwork, PolicyNetwork, ValueNetwork, CombinedNetwork,
    PPOAgent, A2CAgent, create_agent,
    ForexRewardFunction, create_reward_function
)

def test_integration():
    """Test integration of all model components"""
    logger.info("Testing model integration...")
    
    # Test parameters
    batch_size = 8
    state_dim = 300
    action_dim = 20
    
    # Create test data
    states = torch.randn(batch_size, state_dim)
    price_changes = torch.randn(batch_size, action_dim) * 0.01  # Small price changes
    
    logger.info("✓ Test data created")
    
    # 1. Test reward function
    reward_fn = create_reward_function()
    
    # Test with sample actions
    sample_actions = torch.randn(batch_size, action_dim)
    rewards, details = reward_fn(sample_actions, price_changes, return_details=True)
    
    assert rewards.shape == (batch_size,), f"Expected rewards shape ({batch_size},), got {rewards.shape}"
    assert 'final_positions' in details, "Missing final_positions in reward details"
    
    logger.info(f"✓ Reward function test passed - rewards: {rewards.mean().item():.4f}")
    
    # 2. Test PPO agent
    ppo_agent = create_agent('PPO')
    
    # Test action selection
    action, log_prob, value = ppo_agent.select_action(states[0:1])
    assert action.shape == (1, action_dim), f"Expected action shape (1, {action_dim}), got {action.shape}"
    
    logger.info("✓ PPO agent action selection test passed")
    
    # 3. Test A2C agent
    a2c_agent = create_agent('A2C')
    
    # Test action selection
    action, log_prob, value = a2c_agent.select_action(states[0:1])
    assert action.shape == (1, action_dim), f"Expected action shape (1, {action_dim}), got {action.shape}"
    
    logger.info("✓ A2C agent action selection test passed")
    
    # 4. Test end-to-end workflow
    logger.info("Testing end-to-end workflow...")
    
    # Simulate a trading episode
    episode_rewards = []
    episode_actions = []
    
    for step in range(5):  # 5 steps
        # Agent selects action
        action, log_prob, value = ppo_agent.select_action(states[step:step+1])
        
        # Calculate reward using reward function
        step_price_changes = price_changes[step:step+1]
        reward = reward_fn(action, step_price_changes)
        
        episode_rewards.append(reward.item())
        episode_actions.append(action)
        
        logger.info(f"  Step {step+1}: action_mean={action.mean().item():.4f}, reward={reward.item():.4f}")
    
    total_reward = sum(episode_rewards)
    logger.info(f"✓ End-to-end workflow test passed - total reward: {total_reward:.4f}")
    
    # 5. Test training update (simplified)
    logger.info("Testing training update...")
    
    # Create experiences for training
    experiences = {
        'states': states,
        'actions': torch.stack(episode_actions + [torch.randn(1, action_dim)] * (batch_size - len(episode_actions))),
        'rewards': torch.tensor(episode_rewards + [0.0] * (batch_size - len(episode_rewards)), dtype=torch.float32),
        'next_states': torch.roll(states, 1, dims=0),  # Shifted states
        'dones': torch.zeros(batch_size, dtype=torch.bool),
        'log_probs': torch.randn(batch_size),
        'values': torch.randn(batch_size)
    }
    
    # Test PPO update
    stats = ppo_agent.update(experiences)
    assert 'policy_loss' in stats, "Missing policy_loss in training stats"
    assert 'value_loss' in stats, "Missing value_loss in training stats"
    
    logger.info(f"✓ PPO training update test passed - policy_loss: {stats['policy_loss']:.4f}")
    
    # Test A2C update
    stats = a2c_agent.update(experiences)
    assert 'policy_loss' in stats, "Missing policy_loss in training stats"
    
    logger.info(f"✓ A2C training update test passed - policy_loss: {stats['policy_loss']:.4f}")
    
    # 6. Test checkpoint saving/loading
    logger.info("Testing checkpoint functionality...")
    
    # Save agent checkpoint
    checkpoint_path = "test_agent_checkpoint.pt"
    ppo_agent.save_checkpoint(checkpoint_path)
    
    # Create new agent and load checkpoint
    new_agent = create_agent('PPO')
    new_agent.load_checkpoint(checkpoint_path)
    
    # Test that loaded agent produces same output (deterministic mode)
    original_action, _, _ = ppo_agent.select_action(states[0:1], deterministic=True)
    loaded_action, _, _ = new_agent.select_action(states[0:1], deterministic=True)
    
    # Should be very close (allowing for small numerical differences)
    action_diff = torch.abs(original_action - loaded_action).max().item()
    assert action_diff < 1e-3, f"Loaded agent produces different actions: diff={action_diff}"
    
    logger.info("✓ Checkpoint save/load test passed")
    
    # Clean up
    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)
    
    # 7. Test reward function state management
    logger.info("Testing reward function state management...")
    
    # Reset reward function and test state
    reward_fn.reset_state()
    initial_state = reward_fn.get_state()
    
    # Process some rewards to change state
    for _ in range(3):
        _ = reward_fn(torch.randn(1, action_dim), torch.randn(1, action_dim) * 0.01)
    
    final_state = reward_fn.get_state()
    
    # State should have changed
    assert initial_state['mu'] != final_state['mu'], "Reward function state not updating"
    
    logger.info("✓ Reward function state management test passed")
    
    return True

def test_performance():
    """Test performance of model components"""
    logger.info("Testing model performance...")
    
    import time
    
    # Test parameters
    batch_size = 32
    state_dim = 300
    action_dim = 20
    n_iterations = 100
    
    # Create test data
    states = torch.randn(batch_size, state_dim)
    actions = torch.randn(batch_size, action_dim)
    price_changes = torch.randn(batch_size, action_dim) * 0.01
    
    # Test agent inference speed
    agent = create_agent('PPO')
    
    start_time = time.time()
    for _ in range(n_iterations):
        action, log_prob, value = agent.select_action(states)
    inference_time = time.time() - start_time
    
    inference_per_second = (n_iterations * batch_size) / inference_time
    logger.info(f"✓ Agent inference: {inference_per_second:.1f} samples/second")
    
    # Test reward function speed
    reward_fn = create_reward_function()
    
    start_time = time.time()
    for _ in range(n_iterations):
        rewards = reward_fn(actions, price_changes)
    reward_time = time.time() - start_time
    
    reward_per_second = (n_iterations * batch_size) / reward_time
    logger.info(f"✓ Reward function: {reward_per_second:.1f} samples/second")
    
    # Performance requirements check
    min_inference_speed = 1000  # samples/second
    min_reward_speed = 5000     # samples/second
    
    assert inference_per_second > min_inference_speed, f"Inference too slow: {inference_per_second:.1f} < {min_inference_speed}"
    assert reward_per_second > min_reward_speed, f"Reward calculation too slow: {reward_per_second:.1f} < {min_reward_speed}"
    
    logger.info("✓ Performance requirements met")
    
    return True

def main():
    """Run all integration tests"""
    logger.info("="*60)
    logger.info("FOREX RL MODEL INTEGRATION TESTS")
    logger.info("="*60)
    
    try:
        # Test integration
        test_integration()
        logger.info("✅ Integration tests passed")
        
        # Test performance
        test_performance()
        logger.info("✅ Performance tests passed")
        
        logger.info("="*60)
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ Phase 2 Model Implementation Complete")
        logger.info("="*60)
        
        # Summary
        logger.info("Phase 2 Achievements:")
        logger.info("• ✅ Neural Network Architecture (300→512→256→128→20)")
        logger.info("• ✅ Policy and Value Networks")
        logger.info("• ✅ PPO and A2C Agents")
        logger.info("• ✅ Comprehensive Reward Function")
        logger.info("• ✅ Experience Buffer")
        logger.info("• ✅ Checkpoint Management")
        logger.info("• ✅ Performance Optimization")
        logger.info("")
        logger.info("🚀 Ready for Phase 3: Training Environment & Loop")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 