#!/usr/bin/env python
"""
Lightweight version of the fusion autoencoder that runs on a small subset 
of data to validate the approach before running full training.

This script also keeps the ScaledTanhInput layer which already implements
learned normalization via trainable scale and bias parameters.
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import time
import os
import sys
from pathlib import Path
import pandas as pd

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.autoencoder_fusion import (
    get_conn, get_selected_features_per_instrument, load_instrument_data,
    ScaledTanhInput, Autoencoder, preprocess_data
)


def train_small_autoencoder(X, feature_names, n_epochs=50):
    """
    Train a smaller version of the autoencoder for quick validation.
    
    Note: The model already includes the ScaledTanhInput layer which implements
    learned normalization through trainable scale and bias parameters.
    """
    print("\nTraining small autoencoder for validation...")
    
    # Use a smaller architecture
    n_features = X.shape[1]
    bottleneck_dim = 32  # Smaller bottleneck for faster training
    
    # Use CPU for simplicity
    device = torch.device('cpu')
    
    # Initialize model (note that it already has ScaledTanhInput layer)
    model = Autoencoder(n_features, bottleneck_dim).to(device)
    
    # Use Adam optimizer with higher learning rate for faster convergence
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    # Loss function
    criterion = nn.MSELoss()
    
    # Prepare data
    X = X.astype(np.float32)
    # Compute basic statistics before normalization
    print(f"Data statistics before normalization:")
    print(f"- Mean: {np.mean(X):.4f}")
    print(f"- Std: {np.std(X):.4f}")
    print(f"- Min: {np.min(X):.4f}")
    print(f"- Max: {np.max(X):.4f}")
    print(f"- Zero values: {np.sum(X == 0) / X.size:.2%}")
    
    # Simple normalization for training
    mean = np.mean(X, axis=0, keepdims=True)
    std = np.std(X, axis=0, keepdims=True)
    std[std == 0] = 1  # Avoid division by zero
    X_norm = (X - mean) / std
    
    # Convert to tensor
    X_tensor = torch.tensor(X_norm, dtype=torch.float32)
    dataset = TensorDataset(X_tensor)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    # Training loop
    print(f"\nStarting training for {n_epochs} epochs...")
    for epoch in range(n_epochs):
        model.train()
        epoch_loss = 0
        
        for batch_idx, (data,) in enumerate(dataloader):
            data = data.to(device)
            
            # Forward pass
            recon = model(data)
            loss = criterion(recon, data)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
        
        # Print progress
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{n_epochs}, Loss: {epoch_loss/len(dataloader):.6f}")
    
    # Analyze the learned scale and bias parameters
    print("\nLearned normalization parameters (ScaledTanhInput layer):")
    input_layer = model.input_layer
    scale = input_layer.scale.detach().numpy()
    bias = input_layer.bias.detach().numpy()
    
    print(f"Scale statistics:")
    print(f"- Mean: {np.mean(scale):.4f}")
    print(f"- Min: {np.min(scale):.4f}")
    print(f"- Max: {np.max(scale):.4f}")
    
    print(f"\nBias statistics:")
    print(f"- Mean: {np.mean(bias):.4f}")
    print(f"- Min: {np.min(bias):.4f}")
    print(f"- Max: {np.max(bias):.4f}")
    
    # Show example reconstructions
    model.eval()
    with torch.no_grad():
        # Take first 3 samples
        samples = X_tensor[:3]
        recon = model(samples)
        
        # Denormalize
        samples_np = samples.numpy() * std + mean
        recon_np = recon.numpy() * std + mean
        
        print("\nExample reconstructions (first 3 samples, first 5 features):")
        for i in range(3):
            print(f"\nSample {i+1}:")
            for j in range(5):
                if j < len(feature_names):
                    name = feature_names[j]
                    orig = samples_np[i, j]
                    rec = recon_np[i, j]
                    err = abs(orig - rec)
                    err_pct = (err / (abs(orig) + 1e-10)) * 100
                    print(f"{name}: Orig={orig:.4f}, Recon={rec:.4f}, Err={err:.4f} ({err_pct:.2f}%)")
    
    return model


def main():
    """Run a small validation and training on a subset of data."""
    print("Running lightweight autoencoder validation\n")
    
    # Load a small subset of data
    print("Loading a small subset of data...")
    
    # Get instrument to features mapping
    instrument_features = get_selected_features_per_instrument()
    
    # Select just a few instruments for quick testing
    sample_instruments = PAIRS_BY_LIQUIDITY_OANDA[:5]  # Just 5 forex pairs
    
    # Load small sample
    df, feature_names = load_instrument_data(
        target_instruments=sample_instruments,
        instrument_feature_map=instrument_features,
        table_name='forex_features',
        n_rows=50  # Small number of rows
    )
    
    if df is None or df.empty:
        print("Error: No data loaded!")
        return
    
    # Convert to numpy array for processing
    X = df.values.astype(np.float32)
    
    print(f"\nLoaded data: {X.shape[0]} samples, {X.shape[1]} features")
    
    # Apply preprocessing
    print("Preprocessing data...")
    X_processed, feature_names_processed = preprocess_data(X, feature_names)
    
    # Train small autoencoder
    model = train_small_autoencoder(X_processed, feature_names_processed)
    
    print("\nSmall autoencoder training complete!")
    print("\nThe model uses ScaledTanhInput layer which already implements learned")
    print("normalization through trainable scale and bias parameters for each input feature.")
    print("This approach allows the model to learn optimal scaling for each feature during training.")


if __name__ == "__main__":
    main() 