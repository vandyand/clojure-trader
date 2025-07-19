#!/usr/bin/env python
"""
Benchmark the improved fusion autoencoder by evaluating its performance
on both forex and ETF datasets with detailed metrics.
"""
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from pathlib import Path
import time
from typing import List, Dict, Tuple
from sklearn.metrics import r2_score

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.autoencoder_fusion import (
    get_conn, get_selected_features_per_instrument, load_instrument_data
)
from rl.data.test_autoencoder import (
    load_model, preprocess_data_for_test
)

def benchmark_reconstruction(model, X, feature_names, dataset_name='Dataset'):
    """Benchmark reconstruction quality with detailed metrics."""
    print(f"\n=== Benchmarking {dataset_name} ===")
    print(f"Input shape: {X.shape}")
    
    with torch.no_grad():
        # Check input size compatibility with model
        model_input_size = model.encoder[0].in_features
        data_input_size = X.shape[1]
        
        if model_input_size != data_input_size:
            print(f"Input size mismatch. Model expects {model_input_size} features, but data has {data_input_size}.")
            
            # Create a zero-padded array
            padded_X = np.zeros((X.shape[0], model_input_size), dtype=np.float32)
            
            # Copy available features
            min_features = min(model_input_size, data_input_size)
            padded_X[:, :min_features] = X[:, :min_features]
            
            X_padded = padded_X
        else:
            X_padded = X
            min_features = data_input_size
        
        # Convert to tensor
        X_tensor = torch.tensor(X_padded, dtype=torch.float32)
        
        # Apply normalization if the model has data_mean and data_std
        if hasattr(model, 'data_mean') and hasattr(model, 'data_std'):
            print("Applying model's normalization parameters")
            mean = model.data_mean.cpu().numpy()
            std = model.data_std.cpu().numpy()
            
            # Create normalized tensor with zeros
            X_norm = torch.zeros_like(X_tensor)
            
            # Apply normalization to available features
            min_features_norm = min(len(mean), X_tensor.shape[1])
            X_norm_np = ((X_tensor[:, :min_features_norm].numpy() - mean[:min_features_norm]) / 
                         std[:min_features_norm])
            X_norm[:, :min_features_norm] = torch.tensor(X_norm_np, dtype=torch.float32)
            
            X_tensor = X_norm
        
        # Time the encoding and reconstruction operations
        start_time = time.time()
        
        # Get bottleneck representations
        bottleneck = model.encode(X_tensor)
        
        # Get reconstructions
        reconstructed = model(X_tensor)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Convert to numpy arrays
        bottleneck = bottleneck.cpu().numpy()
        reconstructed = reconstructed.cpu().numpy()
        
        # Denormalize reconstructed data if needed
        if hasattr(model, 'data_mean') and hasattr(model, 'data_std'):
            # Only denormalize the features we have
            min_features_denorm = min(len(mean), reconstructed.shape[1])
            reconstructed_subset = reconstructed[:, :min_features_denorm] * std[:min_features_denorm] + mean[:min_features_denorm]
            
            # Replace the denormalized part in the original array
            reconstructed_np = reconstructed.copy()
            reconstructed_np[:, :min_features_denorm] = reconstructed_subset
            reconstructed = reconstructed_np
        
        # Calculate errors (only on the available features)
        min_features_eval = min(X.shape[1], reconstructed.shape[1])
        X_subset = X[:, :min_features_eval]
        recon_subset = reconstructed[:, :min_features_eval]
        
        mse = np.mean((X_subset - recon_subset) ** 2)
        mae = np.mean(np.abs(X_subset - recon_subset))
        
        # Calculate per-feature metrics
        feature_metrics = []
        for i in range(min_features_eval):
            if i < len(feature_names):
                feature_name = feature_names[i]
            else:
                feature_name = f"Feature {i}"
                
            # Get the feature values
            orig = X_subset[:, i]
            recon = recon_subset[:, i]
            
            # Calculate metrics
            feature_mse = np.mean((orig - recon) ** 2)
            feature_mae = np.mean(np.abs(orig - recon))
            
            # Calculate R² score
            try:
                r2 = r2_score(orig, recon)
                # Cap R² at 1.0 and -1.0 to handle numerical issues
                r2 = max(min(r2, 1.0), -1.0)
            except:
                r2 = float('nan')
            
            # Calculate percentage of zero values
            zero_percent = np.mean(orig == 0) * 100
            
            feature_metrics.append({
                'name': feature_name,
                'mse': feature_mse,
                'mae': feature_mae,
                'r2': r2,
                'zero_percent': zero_percent
            })
        
        # Calculate bottleneck statistics
        bottleneck_stats = {
            'mean': np.mean(bottleneck),
            'std': np.std(bottleneck),
            'min': np.min(bottleneck),
            'max': np.max(bottleneck),
            'active_dims': np.mean(np.abs(bottleneck) > 0.1, axis=0).sum(),
            'total_dims': bottleneck.shape[1]
        }
        
        # Print performance metrics
        print(f"\nPerformance Metrics ({dataset_name}):")
        print(f"Processing time for {X.shape[0]} samples: {processing_time:.4f} seconds")
        print(f"Samples per second: {X.shape[0] / processing_time:.2f}")
        
        print(f"\nReconstruction Error ({min_features_eval} features):")
        print(f"MSE: {mse:.6f}")
        print(f"MAE: {mae:.6f}")
        
        print(f"\nBottleneck Analysis:")
        print(f"Dimensions: {bottleneck_stats['total_dims']}")
        print(f"Active dimensions: {bottleneck_stats['active_dims']:.1f}")
        print(f"Mean activation: {bottleneck_stats['mean']:.4f}")
        print(f"Std: {bottleneck_stats['std']:.4f}")
        
        # Print top 5 best reconstructed features
        print("\nTop 5 Best Reconstructed Features:")
        sorted_metrics = sorted(feature_metrics, key=lambda x: x['r2'] if not np.isnan(x['r2']) else -float('inf'), reverse=True)
        for i, metrics in enumerate(sorted_metrics[:5]):
            print(f"{i+1}. {metrics['name']:<30} R²: {metrics['r2']:>8.4f} MSE: {metrics['mse']:>12.4f} %zeros: {metrics['zero_percent']:>5.1f}")
        
        # Print top 5 worst reconstructed features
        print("\nTop 5 Worst Reconstructed Features:")
        for i, metrics in enumerate(sorted_metrics[-5:]):
            print(f"{i+1}. {metrics['name']:<30} R²: {metrics['r2']:>8.4f} MSE: {metrics['mse']:>12.4f} %zeros: {metrics['zero_percent']:>5.1f}")
        
        # Return all metrics for further analysis
        return {
            'mse': mse,
            'mae': mae,
            'processing_time': processing_time,
            'samples_per_second': X.shape[0] / processing_time,
            'feature_metrics': feature_metrics,
            'bottleneck_stats': bottleneck_stats,
            'reconstructed': reconstructed[:, :min_features_eval],
            'bottleneck': bottleneck
        }

def main():
    """Benchmark the autoencoder on forex and ETF datasets."""
    print("Benchmarking the Improved Fusion Autoencoder")
    
    # Load the model
    model, model_feature_names = load_model()
    if model is None:
        return
    
    # Get features for each instrument
    instrument_to_features_map = get_selected_features_per_instrument()
    
    # Load forex data
    print("\nLoading forex data for benchmarking...")
    fx_pairs = PAIRS_BY_LIQUIDITY_OANDA[:10]  # Use first 10 pairs for benchmark
    df_fx, fx_feature_names = load_instrument_data(
        target_instruments=fx_pairs,
        instrument_feature_map=instrument_to_features_map,
        table_name='forex_features',
        n_rows=100  # Use 100 samples for benchmark
    )
    
    # Find ETF instruments
    etf_symbols = []
    all_instruments = sorted(list(instrument_to_features_map.keys()))
    for inst in all_instruments:
        if inst not in PAIRS_BY_LIQUIDITY_OANDA:
            etf_symbols.append(inst)
            if len(etf_symbols) >= 10:  # Limit to 10 ETFs for benchmark
                break
    
    # Load ETF data
    print("\nLoading ETF data for benchmarking...")
    df_etf, etf_feature_names = load_instrument_data(
        target_instruments=etf_symbols,
        instrument_feature_map=instrument_to_features_map,
        table_name='etf_features',
        n_rows=100  # Use 100 samples for benchmark
    )
    
    # Preprocess data
    X_fx, _ = preprocess_data_for_test(df_fx, fx_feature_names)
    X_etf, _ = preprocess_data_for_test(df_etf, etf_feature_names)
    
    # Benchmark on forex data
    fx_metrics = benchmark_reconstruction(model, X_fx, fx_feature_names, dataset_name='Forex')
    
    # Benchmark on ETF data
    etf_metrics = benchmark_reconstruction(model, X_etf, etf_feature_names, dataset_name='ETF')
    
    print("\nBenchmark completed.")

if __name__ == "__main__":
    main() 