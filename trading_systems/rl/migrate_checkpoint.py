#!/usr/bin/env python
"""
Checkpoint Migration Tool

This script provides utilities to migrate checkpoints between different model versions 
or architectural changes. It's particularly useful when the model architecture has been 
updated but you want to preserve the learned weights as much as possible.

Features:
- Analyze checkpoint structure
- Compare different checkpoints
- Migrate parameters between incompatible checkpoints
- Modify network dimensions while preserving weights
- Fix corrupted checkpoints
"""

import os
import sys
import torch
import numpy as np
import argparse
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.checkpoint_compat import ModelCheckpointAdapter
from rl.policy_network import RLTrader, PolicyNetwork, ValueNetwork

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"migrate_checkpoint_{os.path.basename(__file__).split('.')[0]}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CheckpointMigration")

def analyze_checkpoint(checkpoint_path: str) -> Dict:
    """
    Analyze a checkpoint file and print its structure.
    
    Args:
        checkpoint_path: Path to the checkpoint file
        
    Returns:
        Dictionary with checkpoint analysis
    """
    if not os.path.exists(checkpoint_path):
        logger.error(f"Checkpoint file not found: {checkpoint_path}")
        return {}
        
    logger.info(f"Analyzing checkpoint: {checkpoint_path}")
    
    adapter = ModelCheckpointAdapter()
    checkpoint_info = adapter.analyze_checkpoint(checkpoint_path)
    
    # Print structure
    logger.info("Checkpoint structure:")
    for network_type, layer_info in checkpoint_info.items():
        if network_type in ['actor', 'critic']:
            logger.info(f"\n--- {network_type.upper()} NETWORK ---")
            for layer_name, details in layer_info.items():
                if isinstance(details, dict) and 'shape' in details:
                    logger.info(f"  {layer_name}: {details['shape']} ({details.get('type', 'unknown')})")
    
    # Print metadata
    if 'has_metrics' in checkpoint_info:
        logger.info("\n--- METRICS ---")
        logger.info(f"  Has metrics: {checkpoint_info['has_metrics']}")
        if checkpoint_info['has_metrics'] and 'metric_keys' in checkpoint_info:
            logger.info(f"  Metric keys: {checkpoint_info['metric_keys']}")
    
    return checkpoint_info

def compare_checkpoints(source_path: str, target_path: str) -> Dict:
    """
    Compare two checkpoint files.
    
    Args:
        source_path: Path to the source checkpoint
        target_path: Path to the target checkpoint
        
    Returns:
        Dictionary with comparison results
    """
    if not os.path.exists(source_path) or not os.path.exists(target_path):
        logger.error("One or both checkpoint files not found")
        return {}
        
    logger.info(f"Comparing checkpoints:\n  Source: {source_path}\n  Target: {target_path}")
    
    adapter = ModelCheckpointAdapter()
    source_info = adapter.analyze_checkpoint(source_path)
    target_info = adapter.analyze_checkpoint(target_path)
    
    comparison = {
        'network_types': {
            'source_only': [],
            'target_only': [],
            'both': []
        },
        'layers': {
            'source_only': [],
            'target_only': [],
            'matching': [],
            'dimension_mismatch': []
        }
    }
    
    # Compare network types
    source_networks = [net for net in ['actor', 'critic'] if net in source_info]
    target_networks = [net for net in ['actor', 'critic'] if net in target_info]
    
    comparison['network_types']['source_only'] = [net for net in source_networks if net not in target_networks]
    comparison['network_types']['target_only'] = [net for net in target_networks if net not in source_networks]
    comparison['network_types']['both'] = [net for net in source_networks if net in target_networks]
    
    # Compare layers
    for net_type in comparison['network_types']['both']:
        source_layers = source_info[net_type]
        target_layers = target_info[net_type]
        
        # Check each source layer
        for layer_name, layer_details in source_layers.items():
            if layer_name in target_layers:
                source_shape = layer_details.get('shape')
                target_shape = target_layers[layer_name].get('shape')
                
                if source_shape == target_shape:
                    comparison['layers']['matching'].append({
                        'network': net_type,
                        'name': layer_name,
                        'shape': source_shape
                    })
                else:
                    comparison['layers']['dimension_mismatch'].append({
                        'network': net_type,
                        'name': layer_name,
                        'source_shape': source_shape,
                        'target_shape': target_shape
                    })
            else:
                # Check if there's a matching normalized name
                normalized_name = adapter._normalize_layer_name(layer_name)
                matching_keys = [k for k in target_layers 
                               if adapter._normalize_layer_name(k) == normalized_name]
                
                if matching_keys:
                    target_key = matching_keys[0]
                    source_shape = layer_details.get('shape')
                    target_shape = target_layers[target_key].get('shape')
                    
                    if source_shape == target_shape:
                        comparison['layers']['matching'].append({
                            'network': net_type,
                            'source_name': layer_name,
                            'target_name': target_key,
                            'shape': source_shape
                        })
                    else:
                        comparison['layers']['dimension_mismatch'].append({
                            'network': net_type,
                            'source_name': layer_name,
                            'target_name': target_key,
                            'source_shape': source_shape,
                            'target_shape': target_shape
                        })
                else:
                    comparison['layers']['source_only'].append({
                        'network': net_type,
                        'name': layer_name,
                        'shape': layer_details.get('shape')
                    })
        
        # Find target-only layers
        for layer_name, layer_details in target_layers.items():
            normalized_name = adapter._normalize_layer_name(layer_name)
            if not any(adapter._normalize_layer_name(k) == normalized_name for k in source_layers):
                comparison['layers']['target_only'].append({
                    'network': net_type,
                    'name': layer_name,
                    'shape': layer_details.get('shape')
                })
    
    # Print comparison summary
    logger.info("\n--- COMPARISON SUMMARY ---")
    logger.info(f"Network types in both: {comparison['network_types']['both']}")
    logger.info(f"Network types only in source: {comparison['network_types']['source_only']}")
    logger.info(f"Network types only in target: {comparison['network_types']['target_only']}")
    logger.info(f"Matching layers: {len(comparison['layers']['matching'])}")
    logger.info(f"Dimension mismatches: {len(comparison['layers']['dimension_mismatch'])}")
    logger.info(f"Layers only in source: {len(comparison['layers']['source_only'])}")
    logger.info(f"Layers only in target: {len(comparison['layers']['target_only'])}")
    
    # Print dimension mismatches
    if comparison['layers']['dimension_mismatch']:
        logger.info("\n--- DIMENSION MISMATCHES ---")
        for mismatch in comparison['layers']['dimension_mismatch']:
            src_name = mismatch.get('source_name', mismatch.get('name'))
            tgt_name = mismatch.get('target_name', mismatch.get('name'))
            logger.info(f"  {mismatch['network']}: {src_name} -> {tgt_name}")
            logger.info(f"    Source shape: {mismatch['source_shape']}")
            logger.info(f"    Target shape: {mismatch['target_shape']}")
    
    return comparison

def migrate_checkpoint(
    source_path: str, 
    target_path: str, 
    bottleneck_dim: Optional[int] = None,
    num_instruments: Optional[int] = None,
    allow_partial: bool = True
) -> bool:
    """
    Migrate a checkpoint from source to target with possible architecture changes.
    
    Args:
        source_path: Path to the source checkpoint
        target_path: Path to save the migrated checkpoint
        bottleneck_dim: Optional new bottleneck dimension (if changing)
        num_instruments: Optional new number of instruments (if changing)
        allow_partial: Whether to allow partial parameter loading
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(source_path):
        logger.error(f"Source checkpoint not found: {source_path}")
        return False
        
    try:
        # Load source checkpoint
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        source_checkpoint = torch.load(source_path, map_location=device)
        
        # Extract parameters from source checkpoint
        if bottleneck_dim is None:
            # Try to detect from checkpoint
            for key, value in source_checkpoint.get('actor_state_dict', {}).items():
                if 'weight' in key and isinstance(value, torch.Tensor) and len(value.shape) == 2:
                    bottleneck_dim = value.shape[1]  # Input dim is usually second dimension
                    logger.info(f"Detected bottleneck dimension: {bottleneck_dim}")
                    break
            
            if bottleneck_dim is None:
                bottleneck_dim = 149  # Default
                logger.info(f"Using default bottleneck dimension: {bottleneck_dim}")
        
        if num_instruments is None:
            # Try to detect from checkpoint
            for key, value in source_checkpoint.get('actor_state_dict', {}).items():
                if 'mean_head.weight' in key and isinstance(value, torch.Tensor):
                    num_instruments = value.shape[0]  # Output dim is usually first dimension
                    logger.info(f"Detected number of instruments: {num_instruments}")
                    break
            
            if num_instruments is None:
                num_instruments = 20  # Default
                logger.info(f"Using default number of instruments: {num_instruments}")
        
        # Create new policy and value networks with the specified dimensions
        logger.info(f"Creating new networks with bottleneck_dim={bottleneck_dim}, n_instruments={num_instruments}")
        policy_network = PolicyNetwork(bottleneck_dim=bottleneck_dim, n_instruments=num_instruments)
        value_network = ValueNetwork(bottleneck_dim=bottleneck_dim)
        
        # Create adapter for compatibility handling
        adapter = ModelCheckpointAdapter(device=device)
        
        # Load parameters with compatibility handling
        logger.info("Loading actor network parameters...")
        actor_result = adapter.adapt_checkpoint_to_model(
            model=policy_network,
            checkpoint_path=source_path,
            allow_partial_load=allow_partial
        )
        
        logger.info("Loading critic network parameters...")
        critic_result = adapter.adapt_checkpoint_to_model(
            model=value_network,
            checkpoint_path=source_path,
            allow_partial_load=allow_partial
        )
        
        # Create a new RLTrader instance
        trader = RLTrader()
        trader.actor = policy_network
        trader.critic = value_network
        trader.actor_optimizer = torch.optim.Adam(policy_network.parameters(), lr=1e-4)
        trader.critic_optimizer = torch.optim.Adam(value_network.parameters(), lr=1e-3)
        
        # Copy metrics if available
        if 'metrics' in source_checkpoint:
            trader.metrics = source_checkpoint['metrics']
        
        # Save the new checkpoint
        logger.info(f"Saving migrated checkpoint to {target_path}")
        trader.save_model(target_path)
        
        # Log results
        logger.info("\n--- MIGRATION SUMMARY ---")
        logger.info(f"Actor: Loaded {actor_result['loaded_params']}/{actor_result['total_params']} parameters")
        logger.info(f"Critic: Loaded {critic_result['loaded_params']}/{critic_result['total_params']} parameters")
        logger.info(f"New bottleneck dimension: {bottleneck_dim}")
        logger.info(f"New number of instruments: {num_instruments}")
        logger.info(f"Migrated checkpoint saved to: {target_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during checkpoint migration: {e}", exc_info=True)
        return False

def fix_corrupted_checkpoint(
    source_path: str, 
    target_path: str,
    recreate_optimizers: bool = True
) -> bool:
    """
    Attempt to fix a corrupted checkpoint by loading what's possible and recreating the rest.
    
    Args:
        source_path: Path to the corrupted checkpoint
        target_path: Path to save the fixed checkpoint
        recreate_optimizers: Whether to recreate optimizer states
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(source_path):
        logger.error(f"Source checkpoint not found: {source_path}")
        return False
        
    try:
        # First analyze the checkpoint to see what's available
        adapter = ModelCheckpointAdapter()
        checkpoint_info = adapter.analyze_checkpoint(source_path)
        
        # Determine if we have actor and critic state dicts
        has_actor = 'actor' in checkpoint_info
        has_critic = 'critic' in checkpoint_info
        
        if not has_actor and not has_critic:
            logger.error("Checkpoint is too corrupted - no actor or critic state dicts found")
            return False
            
        # Load the checkpoint
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        source_checkpoint = torch.load(source_path, map_location=device)
        
        # Create a new checkpoint with only the valid parts
        new_checkpoint = {}
        
        # Copy actor state dict if available
        if has_actor and 'actor_state_dict' in source_checkpoint:
            new_checkpoint['actor_state_dict'] = source_checkpoint['actor_state_dict']
            
        # Copy critic state dict if available
        if has_critic and 'critic_state_dict' in source_checkpoint:
            new_checkpoint['critic_state_dict'] = source_checkpoint['critic_state_dict']
            
        # Copy metrics if available
        if 'metrics' in source_checkpoint:
            new_checkpoint['metrics'] = source_checkpoint['metrics']
            
        # Recreate optimizer states if requested
        if recreate_optimizers:
            logger.info("Recreating optimizer states")
            
            # Create temporary networks to get optimizers
            bottleneck_dim = None
            n_instruments = None
            
            # Try to detect dimensions from checkpoint
            if has_actor:
                for key, details in checkpoint_info['actor'].items():
                    if 'weight' in key and details.get('type') == 'linear':
                        if bottleneck_dim is None and 'shape' in details:
                            bottleneck_dim = details['shape'][1]  # Input dimension
                        
                        if n_instruments is None and 'mean_head.weight' in key and 'shape' in details:
                            n_instruments = details['shape'][0]  # Output dimension
            
            # Use defaults if not detected
            if bottleneck_dim is None:
                bottleneck_dim = 149
            if n_instruments is None:
                n_instruments = 20
                
            logger.info(f"Creating networks with bottleneck_dim={bottleneck_dim}, n_instruments={n_instruments}")
            
            # Create networks
            policy_network = PolicyNetwork(bottleneck_dim=bottleneck_dim, n_instruments=n_instruments)
            value_network = ValueNetwork(bottleneck_dim=bottleneck_dim)
            
            # Create optimizers
            actor_optimizer = torch.optim.Adam(policy_network.parameters(), lr=1e-4)
            critic_optimizer = torch.optim.Adam(value_network.parameters(), lr=1e-3)
            
            # Save optimizer states
            new_checkpoint['actor_optimizer'] = actor_optimizer.state_dict()
            new_checkpoint['critic_optimizer'] = critic_optimizer.state_dict()
        elif 'actor_optimizer' in source_checkpoint and 'critic_optimizer' in source_checkpoint:
            # Copy optimizer states if available
            new_checkpoint['actor_optimizer'] = source_checkpoint['actor_optimizer']
            new_checkpoint['critic_optimizer'] = source_checkpoint['critic_optimizer']
        
        # Save the new checkpoint
        logger.info(f"Saving fixed checkpoint to {target_path}")
        torch.save(new_checkpoint, target_path)
        
        logger.info("\n--- FIX SUMMARY ---")
        logger.info(f"Actor state dict: {'Preserved' if has_actor else 'Missing'}")
        logger.info(f"Critic state dict: {'Preserved' if has_critic else 'Missing'}")
        logger.info(f"Optimizer states: {'Recreated' if recreate_optimizers else 'Preserved' if 'actor_optimizer' in new_checkpoint else 'Missing'}")
        logger.info(f"Metrics: {'Preserved' if 'metrics' in new_checkpoint else 'Missing'}")
        logger.info(f"Fixed checkpoint saved to: {target_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing corrupted checkpoint: {e}", exc_info=True)
        return False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Checkpoint migration tool")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a checkpoint")
    analyze_parser.add_argument("checkpoint", help="Path to the checkpoint file")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two checkpoints")
    compare_parser.add_argument("source", help="Path to the source checkpoint")
    compare_parser.add_argument("target", help="Path to the target checkpoint")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a checkpoint")
    migrate_parser.add_argument("source", help="Path to the source checkpoint")
    migrate_parser.add_argument("target", help="Path to save the migrated checkpoint")
    migrate_parser.add_argument("--bottleneck-dim", type=int, help="New bottleneck dimension")
    migrate_parser.add_argument("--num-instruments", type=int, help="New number of instruments")
    migrate_parser.add_argument("--allow-partial", action="store_true", help="Allow partial parameter loading")
    
    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix a corrupted checkpoint")
    fix_parser.add_argument("source", help="Path to the corrupted checkpoint")
    fix_parser.add_argument("target", help="Path to save the fixed checkpoint")
    fix_parser.add_argument("--recreate-optimizers", action="store_true", help="Recreate optimizer states")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    if args.command == "analyze":
        analyze_checkpoint(args.checkpoint)
    elif args.command == "compare":
        compare_checkpoints(args.source, args.target)
    elif args.command == "migrate":
        migrate_checkpoint(
            args.source, 
            args.target, 
            bottleneck_dim=args.bottleneck_dim,
            num_instruments=args.num_instruments,
            allow_partial=args.allow_partial
        )
    elif args.command == "fix":
        fix_corrupted_checkpoint(
            args.source, 
            args.target,
            recreate_optimizers=args.recreate_optimizers
        )
    else:
        logger.error("No command specified. Use --help for usage information.")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 