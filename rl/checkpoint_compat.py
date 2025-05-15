import torch
import os
import logging
from typing import Dict, Optional, Tuple, List
import re

logger = logging.getLogger("CheckpointCompat")

class ModelCheckpointAdapter:
    """
    Adapter to handle compatibility issues between saved checkpoints and current model architecture.
    
    This class provides utilities to:
    1. Analyze checkpoint and model architecture for mismatches
    2. Normalize layer naming conventions
    3. Handle dimension mismatches with optional reshaping
    4. Provide detailed diagnostics on compatibility issues
    """
    
    def __init__(self, device=None):
        """Initialize the adapter with the target device."""
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def analyze_checkpoint(self, checkpoint_path: str) -> Dict:
        """
        Analyze a checkpoint file and return information about its structure.
        
        Args:
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            Dictionary with checkpoint metadata
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Extract structure information
        network_info = {}
        
        # Process actor state dict if present
        if 'actor_state_dict' in checkpoint:
            network_info['actor'] = self._analyze_state_dict(checkpoint['actor_state_dict'])
            
        # Process critic state dict if present
        if 'critic_state_dict' in checkpoint:
            network_info['critic'] = self._analyze_state_dict(checkpoint['critic_state_dict'])
        
        # Add metadata
        network_info['has_metrics'] = 'metrics' in checkpoint
        if network_info['has_metrics'] and isinstance(checkpoint['metrics'], dict):
            network_info['metric_keys'] = list(checkpoint['metrics'].keys())
            
        return network_info
    
    def _analyze_state_dict(self, state_dict: Dict) -> Dict:
        """
        Analyze a state dictionary to extract layer information.
        
        Args:
            state_dict: Model state dictionary
            
        Returns:
            Dictionary with layer information
        """
        layer_info = {}
        
        # Extract layer names and shapes
        for key, param in state_dict.items():
            if isinstance(param, torch.Tensor):
                layer_info[key] = {
                    'shape': list(param.shape),
                    'dtype': str(param.dtype),
                    'requires_grad': param.requires_grad if hasattr(param, 'requires_grad') else None
                }
                
                # Try to identify layer type
                if 'weight' in key:
                    if len(param.shape) == 2:
                        layer_info[key]['type'] = 'linear'
                    elif len(param.shape) == 4:
                        layer_info[key]['type'] = 'conv'
                elif 'bias' in key:
                    layer_info[key]['type'] = 'bias'
                elif 'running_mean' in key or 'running_var' in key:
                    layer_info[key]['type'] = 'batch_norm'
                else:
                    layer_info[key]['type'] = 'other'
        
        return layer_info
    
    def compare_model_with_checkpoint(self, model: torch.nn.Module, checkpoint_path: str) -> Dict:
        """
        Compare a model with a checkpoint to identify mismatches.
        
        Args:
            model: PyTorch model
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            Dictionary with comparison results
        """
        # Get model state dict
        model_state = model.state_dict()
        
        # Analyze checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Determine which state dict to compare with
        target_state = None
        if isinstance(model, torch.nn.Module) and not isinstance(model, torch.nn.Sequential):
            model_name = model.__class__.__name__.lower()
            if 'actor' in model_name and 'actor_state_dict' in checkpoint:
                target_state = checkpoint['actor_state_dict']
            elif 'critic' in model_name and 'critic_state_dict' in checkpoint:
                target_state = checkpoint['critic_state_dict']
            elif 'policy' in model_name and 'actor_state_dict' in checkpoint:
                target_state = checkpoint['actor_state_dict']
            elif 'value' in model_name and 'critic_state_dict' in checkpoint:
                target_state = checkpoint['critic_state_dict']
        
        if target_state is None:
            # If no specific match, try to use any available state dict
            for key in ['state_dict', 'model_state_dict', 'actor_state_dict', 'critic_state_dict']:
                if key in checkpoint:
                    target_state = checkpoint[key]
                    break
        
        if target_state is None:
            raise ValueError("Could not find an appropriate state dict in checkpoint")
            
        # Compare shapes
        comparison = {
            'matching_layers': [],
            'shape_mismatches': [],
            'missing_in_checkpoint': [],
            'missing_in_model': []
        }
        
        # Check each layer in model against checkpoint
        for key, param in model_state.items():
            if key in target_state:
                checkpoint_param = target_state[key]
                if param.shape == checkpoint_param.shape:
                    comparison['matching_layers'].append({
                        'name': key,
                        'shape': list(param.shape)
                    })
                else:
                    comparison['shape_mismatches'].append({
                        'name': key,
                        'model_shape': list(param.shape),
                        'checkpoint_shape': list(checkpoint_param.shape)
                    })
            else:
                # Check for renamed layers
                normalized_key = self._normalize_layer_name(key)
                matching_keys = [k for k in target_state if self._normalize_layer_name(k) == normalized_key]
                
                if matching_keys:
                    checkpoint_key = matching_keys[0]
                    checkpoint_param = target_state[checkpoint_key]
                    
                    if param.shape == checkpoint_param.shape:
                        comparison['matching_layers'].append({
                            'name': key,
                            'checkpoint_name': checkpoint_key,
                            'shape': list(param.shape)
                        })
                    else:
                        comparison['shape_mismatches'].append({
                            'name': key,
                            'checkpoint_name': checkpoint_key,
                            'model_shape': list(param.shape),
                            'checkpoint_shape': list(checkpoint_param.shape)
                        })
                else:
                    comparison['missing_in_checkpoint'].append({
                        'name': key,
                        'shape': list(param.shape)
                    })
        
        # Check for keys in checkpoint that are not in model
        for key in target_state:
            if key not in model_state:
                normalized_key = self._normalize_layer_name(key)
                if not any(self._normalize_layer_name(k) == normalized_key for k in model_state):
                    comparison['missing_in_model'].append({
                        'name': key,
                        'shape': list(target_state[key].shape)
                    })
                    
        return comparison
    
    def _normalize_layer_name(self, name: str) -> str:
        """
        Normalize layer names to handle different naming conventions.
        
        Args:
            name: Original layer name
            
        Returns:
            Normalized layer name for comparison
        """
        # Remove common prefixes like module., encoder., etc.
        name = re.sub(r'^(module\.|encoder\.|decoder\.|backbone\.)', '', name)
        
        # Normalize sequential layer indices
        name = re.sub(r'\.(\d+)\.', r'_\1_', name)
        
        # Remove bn/batch_norm variations
        name = name.replace('batch_norm', 'bn')
        
        # Normalize conv/linear/fc layer names
        if 'conv' in name:
            name = re.sub(r'conv\d*', 'conv', name)
        if any(x in name for x in ['linear', 'fc', 'dense']):
            name = re.sub(r'(linear|fc|dense)\d*', 'linear', name)
            
        return name.lower()
    
    def adapt_checkpoint_to_model(
        self, 
        model: torch.nn.Module, 
        checkpoint_path: str,
        allow_partial_load: bool = True,
        strict: bool = False
    ) -> Dict:
        """
        Load a checkpoint into a model with compatibility handling.
        
        Args:
            model: PyTorch model
            checkpoint_path: Path to the checkpoint file
            allow_partial_load: Whether to allow loading a subset of the model
            strict: Whether to raise an error on missing keys
            
        Returns:
            Dictionary with load results
        """
        # Load checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Get target state dict from checkpoint
        target_state = None
        if isinstance(model, torch.nn.Module) and not isinstance(model, torch.nn.Sequential):
            model_name = model.__class__.__name__.lower()
            if 'actor' in model_name and 'actor_state_dict' in checkpoint:
                target_state = checkpoint['actor_state_dict']
            elif 'critic' in model_name and 'critic_state_dict' in checkpoint:
                target_state = checkpoint['critic_state_dict']
            elif 'policy' in model_name and 'actor_state_dict' in checkpoint:
                target_state = checkpoint['actor_state_dict']
            elif 'value' in model_name and 'critic_state_dict' in checkpoint:
                target_state = checkpoint['critic_state_dict']
        
        if target_state is None:
            # If no specific match, try to use any available state dict
            for key in ['state_dict', 'model_state_dict', 'actor_state_dict', 'critic_state_dict']:
                if key in checkpoint:
                    target_state = checkpoint[key]
                    break
        
        if target_state is None:
            raise ValueError("Could not find an appropriate state dict in checkpoint")
            
        # Create a new state dict for the model
        new_state_dict = {}
        model_state = model.state_dict()
        
        # Process each layer in the model state dict
        for key, param in model_state.items():
            # Try direct matching first
            if key in target_state and param.shape == target_state[key].shape:
                new_state_dict[key] = target_state[key]
                continue
                
            # Try to find a matching layer by normalized name
            normalized_key = self._normalize_layer_name(key)
            matching_keys = [k for k in target_state if self._normalize_layer_name(k) == normalized_key]
            
            if matching_keys:
                checkpoint_key = matching_keys[0]
                checkpoint_param = target_state[checkpoint_key]
                
                # Check if shapes match
                if param.shape == checkpoint_param.shape:
                    new_state_dict[key] = checkpoint_param
                else:
                    # Try to reshape if possible (e.g., for fc or conv layers)
                    try:
                        if len(param.shape) == len(checkpoint_param.shape):
                            # Same dimension but different sizes - skip if they're very different
                            if any(abs(a - b) > min(a, b) for a, b in zip(param.shape, checkpoint_param.shape)):
                                logger.warning(f"Skipping layer {key} due to incompatible dimensions: {param.shape} vs {checkpoint_param.shape}")
                                continue
                                
                            # Try to reshape
                            logger.warning(f"Attempting to reshape layer {key}: {checkpoint_param.shape} -> {param.shape}")
                            reshaped_param = self._reshape_parameter(checkpoint_param, param.shape)
                            new_state_dict[key] = reshaped_param
                        else:
                            logger.warning(f"Dimension mismatch for layer {key}: {len(param.shape)} vs {len(checkpoint_param.shape)} dimensions")
                    except Exception as e:
                        logger.error(f"Failed to reshape layer {key}: {e}")
            elif not strict:
                # If the layer doesn't exist in checkpoint and strict=False, keep the existing weights
                logger.warning(f"Layer {key} not found in checkpoint, keeping current weights")
                
        # Log statistics
        total_params = len(model_state)
        loaded_params = len(new_state_dict)
        logger.info(f"Loaded {loaded_params}/{total_params} parameters ({loaded_params/total_params*100:.1f}%)")
        
        # Load state dict into model with error handling
        if not allow_partial_load and loaded_params < total_params:
            raise ValueError(f"Only {loaded_params}/{total_params} parameters could be loaded")
            
        # Set strict=False to ignore missing keys
        result = model.load_state_dict(new_state_dict, strict=False)
        
        return {
            'loaded_params': loaded_params,
            'total_params': total_params,
            'missing_keys': result.missing_keys,
            'unexpected_keys': result.unexpected_keys
        }
    
    def _reshape_parameter(self, param: torch.Tensor, target_shape: List[int]) -> torch.Tensor:
        """
        Attempt to reshape a parameter to match the target shape.
        
        Args:
            param: Parameter tensor to reshape
            target_shape: Target shape
            
        Returns:
            Reshaped parameter tensor if possible, else the original tensor
        """
        # Handle simple case - just needs reshaping
        if param.numel() == torch.tensor(target_shape).prod().item():
            return param.reshape(target_shape)
        
        # Handle linear layer weight reshaping (most common case)
        if len(param.shape) == 2 and len(target_shape) == 2:
            # Linear layer: in_features x out_features
            old_in, old_out = param.shape
            new_in, new_out = target_shape
            
            if old_out == new_out:
                # Same output size, input size changed
                if new_in > old_in:
                    # Pad with zeros
                    padded = torch.zeros(target_shape, dtype=param.dtype, device=param.device)
                    padded[:old_in, :] = param
                    return padded
                else:
                    # Truncate
                    return param[:new_in, :]
            elif old_in == new_in:
                # Same input size, output size changed
                if new_out > old_out:
                    # Pad with zeros
                    padded = torch.zeros(target_shape, dtype=param.dtype, device=param.device)
                    padded[:, :old_out] = param
                    return padded
                else:
                    # Truncate
                    return param[:, :new_out]
            else:
                # Both dimensions changed
                if new_in > old_in and new_out > old_out:
                    # Pad with zeros
                    padded = torch.zeros(target_shape, dtype=param.dtype, device=param.device)
                    padded[:old_in, :old_out] = param
                    return padded
                elif new_in <= old_in and new_out <= old_out:
                    # Truncate
                    return param[:new_in, :new_out]
                else:
                    # Mixed case
                    padded = torch.zeros(target_shape, dtype=param.dtype, device=param.device)
                    if new_in > old_in:
                        if new_out <= old_out:
                            padded[:old_in, :] = param[:, :new_out]
                            return padded
                    else:
                        if new_out > old_out:
                            padded[:, :old_out] = param[:new_in, :]
                            return padded
        
        # If we can't handle the reshaping, return the original tensor
        raise ValueError(f"Cannot reshape tensor of shape {param.shape} to {target_shape}")


def fix_checkpoint_loading(model, checkpoint_path, allow_partial=True):
    """
    Utility function to attempt fixing checkpoint loading issues.
    
    Args:
        model: The model to load the checkpoint into
        checkpoint_path: Path to the checkpoint file
        allow_partial: Whether to allow partial loading of parameters
        
    Returns:
        True if successful, False otherwise
    """
    adapter = ModelCheckpointAdapter()
    
    try:
        logger.info(f"Analyzing checkpoint: {checkpoint_path}")
        analysis = adapter.analyze_checkpoint(checkpoint_path)
        
        logger.info(f"Comparing model with checkpoint")
        comparison = adapter.compare_model_with_checkpoint(model, checkpoint_path)
        
        # Log compatibility information
        logger.info(f"Found {len(comparison['matching_layers'])} matching layers")
        logger.info(f"Found {len(comparison['shape_mismatches'])} layers with shape mismatches")
        logger.info(f"Found {len(comparison['missing_in_checkpoint'])} layers missing in checkpoint")
        logger.info(f"Found {len(comparison['missing_in_model'])} layers in checkpoint not in model")
        
        if comparison['shape_mismatches']:
            logger.warning("Shape mismatches detected:")
            for mismatch in comparison['shape_mismatches']:
                logger.warning(f"  {mismatch['name']}: {mismatch['model_shape']} vs {mismatch['checkpoint_shape']}")
        
        # Try to load with adaptation
        result = adapter.adapt_checkpoint_to_model(
            model=model,
            checkpoint_path=checkpoint_path,
            allow_partial_load=allow_partial,
            strict=False
        )
        
        logger.info(f"Loaded {result['loaded_params']}/{result['total_params']} parameters")
        if result['missing_keys']:
            logger.warning(f"Missing keys: {result['missing_keys']}")
        if result['unexpected_keys']:
            logger.warning(f"Unexpected keys: {result['unexpected_keys']}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error fixing checkpoint loading: {e}")
        return False 