#!/usr/bin/env python
"""
Test the improved fusion autoencoder by loading the saved model and 
running it on a sample of real data to evaluate reconstruction quality.
"""
import torch
import numpy as np
import sys
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.autoencoder_fusion_improved import (
    ImprovedAutoencoder, get_conn, get_selected_features_per_instrument,
    load_instrument_data, preprocess_data
)

def load_model(model_path='models/fusion_autoencoder.pt'):
    """Load the trained autoencoder model."""
    try:
        checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
        
        # Extract metadata
        input_size = checkpoint['input_size']
        bottleneck_size = checkpoint['bottleneck_size']
        feature_names = checkpoint.get('feature_names', [])
        
        print(f"Input size: {input_size}")
        print(f"Bottleneck size: {bottleneck_size}")
        print(f"Compression ratio: {input_size/bottleneck_size:.2f}x")
        
        # Create model with same architecture
        model = ImprovedAutoencoder(
            n_features=input_size,
            bottleneck_dim=bottleneck_size,
            dropout_rate=0.2
        )
        
        # Split state dict to model parameters and buffers
        model_state_dict = {}
        buffer_state_dict = {}
        for key, value in checkpoint['model_state_dict'].items():
            if key.startswith('data_'):  # data_mean and data_std are buffers
                buffer_state_dict[key] = value
            else:
                model_state_dict[key] = value
        
        # Load weights
        model.load_state_dict(model_state_dict, strict=True)
        
        # Register buffers manually
        if 'data_mean' in buffer_state_dict:
            model.register_buffer('data_mean', buffer_state_dict['data_mean'])
        if 'data_std' in buffer_state_dict:
            model.register_buffer('data_std', buffer_state_dict['data_std'])
            
        model.eval()  # Set to evaluation mode
        
        return model, feature_names
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        return None, []

def test_reconstruction(model, X, feature_names, n_samples=5):
    """Test the reconstruction quality on a few samples."""
    with torch.no_grad():
        X_tensor = torch.tensor(X[:n_samples], dtype=torch.float32)
        
        # Check input size compatibility with model
        model_input_size = model.encoder[0].in_features
        data_input_size = X_tensor.shape[1]
        
        if model_input_size != data_input_size:
            print(f"Warning: Input size mismatch. Model expects {model_input_size} features, but data has {data_input_size}.")
            print("Creating zero-padded tensor to match model input size.")
            
            # Create a zero-padded tensor
            padded_tensor = torch.zeros((X_tensor.shape[0], model_input_size), dtype=torch.float32)
            
            # Copy available features
            min_features = min(model_input_size, data_input_size)
            padded_tensor[:, :min_features] = X_tensor[:, :min_features]
            
            X_tensor = padded_tensor
        
        # Apply normalization if the model has data_mean and data_std
        if hasattr(model, 'data_mean') and hasattr(model, 'data_std'):
            print("Applying normalization with model's parameters")
            mean = model.data_mean.cpu().numpy()
            std = model.data_std.cpu().numpy()
            
            # Create normalized tensor
            X_norm = torch.zeros_like(X_tensor)
            
            # Apply normalization to available features
            min_features = min(len(mean), X_tensor.shape[1])
            X_norm_np = ((X_tensor[:, :min_features].numpy() - mean[:min_features]) / 
                         std[:min_features])
            X_norm[:, :min_features] = torch.tensor(X_norm_np, dtype=torch.float32)
            
            X_tensor = X_norm
        
        # Get bottleneck representations and reconstructions separately
        bottleneck = model.encode(X_tensor)
        reconstructed = model(X_tensor)
        
        # Convert to numpy arrays
        bottleneck = bottleneck.numpy()
        reconstructed = reconstructed.numpy()
        
        # Denormalize reconstructed data if needed
        if hasattr(model, 'data_mean') and hasattr(model, 'data_std'):
            # Only denormalize the features we have
            min_features = min(len(mean), reconstructed.shape[1])
            reconstructed_subset = reconstructed[:, :min_features] * std[:min_features] + mean[:min_features]
            
            # Replace the denormalized part in the original array
            reconstructed_np = reconstructed.copy()
            reconstructed_np[:, :min_features] = reconstructed_subset
            reconstructed = reconstructed_np
        
        # Calculate errors (only on the available features)
        min_features = min(X.shape[1], reconstructed.shape[1])
        mse = np.mean((X[:n_samples, :min_features] - reconstructed[:, :min_features]) ** 2)
        mae = np.mean(np.abs(X[:n_samples, :min_features] - reconstructed[:, :min_features]))
        
        print(f"\nReconstruction Error (on {min_features} features):")
        print(f"MSE: {mse:.6f}")
        print(f"MAE: {mae:.6f}")
        
        # Print bottleneck statistics
        print(f"\nBottleneck Statistics:")
        print(f"Mean: {np.mean(bottleneck):.4f}")
        print(f"Std: {np.std(bottleneck):.4f}")
        print(f"Min: {np.min(bottleneck):.4f}")
        print(f"Max: {np.max(bottleneck):.4f}")
        
        # Print a few feature comparisons (only for available features)
        print("\nFeature comparison (original vs reconstructed):")
        min_features_to_show = min(5, min_features)
        for sample_idx in range(min(3, n_samples)):
            print(f"\nSample {sample_idx + 1}:")
            for i in range(min_features_to_show):
                if i < len(feature_names):
                    feature_name = feature_names[i]
                else:
                    feature_name = f"Feature {i}"
                    
                orig = X[sample_idx, i]
                recon = reconstructed[sample_idx, i]
                error = abs(orig - recon)
                error_pct = error / (abs(orig) + 1e-10) * 100
                print(f"{feature_name:<30} Orig: {orig:>10.4f}  Recon: {recon:>10.4f}  Error: {error:>10.4f} ({error_pct:>6.2f}%)")

def preprocess_data_for_test(df, feature_names):
    """
    Simplified preprocessing function for test data that works with DataFrames.
    """
    print("\nPreprocessing test data...")
    
    # Convert DataFrame to numpy array if needed
    if isinstance(df, pd.DataFrame):
        print(f"Converting DataFrame to numpy array. Shape: {df.shape}")
        X = df.values.astype(np.float32)
    else:
        X = df
        
    # Fill NaN values with 0
    X = np.nan_to_num(X, nan=0.0)
    
    # Clip extreme values
    X = np.clip(X, -1e6, 1e6)
    
    print(f"Processed data shape: {X.shape}")
    return X, feature_names

def main():
    """Test the improved fusion autoencoder."""
    print("Testing the Improved Fusion Autoencoder")
    
    # Load the model
    model, feature_names = load_model()
    if model is None:
        return
    
    # Get selected features per instrument
    instrument_to_features_map = get_selected_features_per_instrument()
    
    # Load a small amount of test data (not used in training)
    df, feature_names_loaded = load_instrument_data(
        target_instruments=PAIRS_BY_LIQUIDITY_OANDA[:5],  # Just use a few instruments
        instrument_feature_map=instrument_to_features_map,
        table_name='forex_features',
        n_rows=50,  # Load a small sample
    )
    
    # If feature_names is empty, use the loaded ones
    if not feature_names:
        feature_names = feature_names_loaded
    
    # Preprocess the data using our simplified function
    X_processed, _ = preprocess_data_for_test(df, feature_names)
    
    # Test the reconstruction
    test_reconstruction(model, X_processed, feature_names)
    
    print("\nTest completed.")

if __name__ == "__main__":
    main() 