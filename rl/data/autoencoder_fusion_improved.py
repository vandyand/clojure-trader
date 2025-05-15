#!/usr/bin/env python
"""
Improved version of the fusion autoencoder that incorporates:
1. 89-dimensional bottleneck (same as forex pairs count in the dataset)
2. Enhanced ScaledTanhInput initialization
3. Dropout regularization for better generalization
4. Larger batch size for faster training
5. Comprehensive data validation across instruments
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import os
import sys
from pathlib import Path
import pandas as pd
from typing import List, Tuple, Dict, Optional
import time

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.autoencoder_fusion import (
    get_conn, get_selected_features_per_instrument, load_instrument_data,
    print_input_stats, save_model, verify_feature_naming_in_db
)


class EnhancedScaledTanhInput(nn.Module):
    """
    Enhanced version of ScaledTanhInput that has better initialization
    based on feature statistics.
    """
    def __init__(self, n_features, feature_stats=None):
        """
        Initialize with optional feature statistics for better scaling.
        
        Args:
            n_features: Number of input features
            feature_stats: Optional dict with 'mean' and 'std' for better initialization
        """
        super().__init__()
        
        # Initialize with ones and zeros as default
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))
        
        # If statistics are provided, use them for better initialization
        if feature_stats is not None:
            # Calculate initial scale based on feature standard deviation
            # We want to map most values to the effective range of tanh (-1 to 1)
            # A good rule is to set scale = 1 / (2 * std) to map most values to this range
            std = np.maximum(feature_stats['std'], 1e-6)  # Avoid division by zero
            initial_scale = 1.0 / (2.0 * std)
            
            # Cap the scales to reasonable values
            initial_scale = np.clip(initial_scale, 0.1, 10.0)
            
            # Calculate initial bias to center the data
            # For tanh, centering at 0 is ideal, so bias = -mean * scale
            initial_bias = -feature_stats['mean'] * initial_scale
            
            # Set as initial values
            self.scale.data = torch.tensor(initial_scale, dtype=torch.float32)
            self.bias.data = torch.tensor(initial_bias, dtype=torch.float32)
    
    def forward(self, x):
        return torch.tanh(self.scale * x + self.bias)


class ImprovedAutoencoder(nn.Module):
    """Improved autoencoder with dropout regularization and better layer sizes."""
    
    def __init__(self, n_features, bottleneck_dim=89, dropout_rate=0.2, feature_stats=None):
        super().__init__()
        self.bottleneck_dim = bottleneck_dim
        
        # Calculate layer sizes with progressive compression
        # More balanced layer sizes for better gradient flow
        hidden_dim1 = max(n_features // 2, bottleneck_dim * 3)
        hidden_dim2 = max(n_features // 4, bottleneck_dim * 2)
        
        # Input scaling layer with enhanced initialization
        self.input_layer = EnhancedScaledTanhInput(n_features, feature_stats)
        
        # Encoder layers with LeakyReLU activation and dropout
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim2, bottleneck_dim),
            nn.Tanh(),  # Keep tanh in bottleneck for bounded representation
            nn.BatchNorm1d(bottleneck_dim)
        )
        
        # Decoder layers with LeakyReLU activation
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim2, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim1, n_features)
        )
        
        # Initialize weights using He initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
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


def validate_data_quality(instrument_feature_map, sample_size=5):
    """
    Validate data quality for a sample of instruments from each type (FX and ETF).
    Returns a summary of data quality issues, if any.
    """
    print("Validating data quality across instruments...")
    
    # Get all instrument names
    all_instruments = sorted(list(instrument_feature_map.keys()))
    
    # Separate FX and ETF instruments
    fx_pairs = [i for i in all_instruments if i in PAIRS_BY_LIQUIDITY_OANDA]
    etf_symbols = [i for i in all_instruments if i not in PAIRS_BY_LIQUIDITY_OANDA]
    
    # Sample instruments to check
    fx_to_check = fx_pairs[:min(sample_size, len(fx_pairs))]
    etf_to_check = etf_symbols[:min(sample_size, len(etf_symbols))]
    
    issues = []
    all_stats = {}
    
    # Check FX data
    print(f"Checking {len(fx_to_check)} Forex instruments...")
    for instrument in fx_to_check:
        stats = check_instrument_data(
            instrument, 
            instrument_feature_map[instrument], 
            'forex_features'
        )
        all_stats[instrument] = stats
        if stats['issues']:
            issues.extend(stats['issues'])
    
    # Check ETF data
    print(f"Checking {len(etf_to_check)} ETF instruments...")
    for instrument in etf_to_check:
        stats = check_instrument_data(
            instrument, 
            instrument_feature_map[instrument], 
            'etf_features'
        )
        all_stats[instrument] = stats
        if stats['issues']:
            issues.extend(stats['issues'])
    
    # Print summary
    print("\nData Quality Summary:")
    print(f"- Total instruments checked: {len(fx_to_check) + len(etf_to_check)}")
    print(f"- Issues found: {len(issues)}")
    
    if issues:
        print("\nTop issues:")
        for issue in issues[:5]:
            print(f"- {issue}")
    
    # Compute overall statistics
    zero_pcts = []
    non_zero_pcts = []
    nan_pcts = []
    
    for stats in all_stats.values():
        zero_pcts.append(stats['zero_pct'])
        non_zero_pcts.append(stats['non_zero_pct'])
        nan_pcts.append(stats['nan_pct'])
    
    print("\nOverall Statistics:")
    print(f"- Average zero values: {np.mean(zero_pcts):.2f}%")
    print(f"- Average non-zero values: {np.mean(non_zero_pcts):.2f}%")
    print(f"- Average NaN values: {np.mean(nan_pcts):.2f}%")
    
    return {
        'issues': issues,
        'stats': all_stats,
        'overall_zero_pct': np.mean(zero_pcts),
        'overall_non_zero_pct': np.mean(non_zero_pcts),
        'overall_nan_pct': np.mean(nan_pcts)
    }


def check_instrument_data(instrument, features, table_name, n_rows=20):
    """
    Check data quality for a specific instrument and its features.
    Returns statistics and issues found.
    """
    conn = get_conn()
    
    # Construct SQL query to get features
    placeholders = ", ".join([f"features->>'{f}' AS \"{f}\"" for f in features])
    query = f"""
    SELECT timestamp, {placeholders}
    FROM {table_name}
    WHERE instrument = '{instrument}' AND granularity = 'D'
    ORDER BY timestamp DESC
    LIMIT {n_rows}
    """
    
    try:
        # Get the data as a pandas DataFrame
        df = pd.read_sql_query(query, conn)
        
        # Basic statistics
        zero_count = (df == 0).sum().sum()
        zero_pct = (df == 0).sum().sum() / (df.size - df.shape[0]) * 100  # Exclude timestamp column
        non_zero_pct = 100 - zero_pct
        nan_count = df.isna().sum().sum()
        nan_pct = df.isna().sum().sum() / (df.size - df.shape[0]) * 100  # Exclude timestamp column
        
        # Check for issues
        issues = []
        
        # Check for NaNs
        nan_cols = df.columns[df.isna().sum() > 0]
        if len(nan_cols) > 0:
            issues.append(f"{instrument}: Found NaNs in columns: {', '.join(nan_cols[:3])}{'...' if len(nan_cols) > 3 else ''}")
        
        # Check for all zeros
        all_zero_cols = df.columns[(df == 0).all()]
        if len(all_zero_cols) > 0:
            issues.append(f"{instrument}: All zero values in columns: {', '.join(all_zero_cols[:3])}{'...' if len(all_zero_cols) > 3 else ''}")
        
        # Check for high percentage of zeros
        high_zero_cols = df.columns[((df == 0).sum() / len(df) > 0.8) & ((df == 0).sum() / len(df) < 1.0)]
        if len(high_zero_cols) > 0:
            issues.append(f"{instrument}: >80% zeros in columns: {', '.join(high_zero_cols[:3])}{'...' if len(high_zero_cols) > 3 else ''}")
        
        return {
            'zero_count': zero_count,
            'zero_pct': zero_pct,
            'non_zero_pct': non_zero_pct,
            'nan_count': nan_count,
            'nan_pct': nan_pct,
            'issues': issues
        }
        
    except Exception as e:
        return {
            'zero_count': 0,
            'zero_pct': 0,
            'non_zero_pct': 0,
            'nan_count': 0,
            'nan_pct': 0,
            'issues': [f"Error checking {instrument}: {str(e)}"]
        }
    finally:
        conn.close()


def preprocess_data(X, feature_names):
    """
    Enhanced preprocessing for financial data with better handling of outliers,
    missing values, and feature scaling.
    
    Args:
        X: Input data array (numpy array)
        feature_names: List of feature names
        
    Returns:
        Tuple of (preprocessed_data, feature_names, feature_stats)
    """
    print("\nPreprocessing data...")
    print(f"Input shape: {X.shape}")
    print(f"Feature count: {len(feature_names)}")
    
    # Initial NaN check
    if np.isnan(X).any():
        nan_count = np.isnan(X).sum()
        nan_percent = nan_count / X.size * 100
        print(f"Warning: Found {nan_count} NaN values ({nan_percent:.2f}%) in input data.")
        
        # Count NaNs by feature
        nan_per_feature = np.isnan(X).sum(axis=0)
        problem_features = [(feature_names[i], nan_per_feature[i]) for i in range(len(feature_names)) if nan_per_feature[i] > 0]
        if problem_features:
            print(f"Features with NaNs: {len(problem_features)}")
            for feature, count in sorted(problem_features, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {feature}: {count} NaNs ({count/X.shape[0]*100:.2f}%)")
        
        # Replace NaNs with 0 (more conservative approach than mean for financial data)
        X = np.nan_to_num(X, nan=0.0)
        print(f"Replaced all NaN values with 0.0")
    
    # Check for infinite values
    if np.isinf(X).any():
        inf_count = np.isinf(X).sum()
        print(f"Warning: Found {inf_count} infinite values in input data.")
        
        # Replace inf with large but finite values
        X = np.clip(X, -1e9, 1e9)
        print(f"Clipped all values to range [-1e9, 1e9]")
    
    # Remove any constant features (zero variance)
    std_per_feature = np.std(X, axis=0)
    constant_features = std_per_feature < 1e-8
    
    if constant_features.any():
        constant_count = constant_features.sum()
        print(f"Found {constant_count} constant features with near-zero variance.")
        
        # List the constant features
        constant_feature_names = [feature_names[i] for i in range(len(feature_names)) if constant_features[i]]
        print(f"Examples of constant features: {constant_feature_names[:5]}")
        
        # Remove constant features
        non_constant_indices = ~constant_features
        X = X[:, non_constant_indices]
        feature_names = [feature_names[i] for i in range(len(feature_names)) if non_constant_indices[i]]
        
        print(f"Removed {constant_count} constant features. New shape: {X.shape}")
    
    # Check for extremely large values that could dominate training
    max_abs_values = np.max(np.abs(X), axis=0)
    extreme_features = max_abs_values > 1e6
    
    if extreme_features.any():
        extreme_count = extreme_features.sum()
        print(f"Found {extreme_count} features with extreme values (abs > 1e6).")
        
        # Log some examples
        extreme_examples = [(feature_names[i], max_abs_values[i]) for i in range(len(feature_names)) 
                            if extreme_features[i]]
        for feature, value in sorted(extreme_examples, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {feature}: max abs value = {value:.2e}")
        
        # Clip extreme values
        X = np.clip(X, -1e6, 1e6)
        print(f"Clipped all values to range [-1e6, 1e6]")
    
    # Compute statistics for normalization
    mean = np.mean(X, axis=0)
    std = np.std(X, axis=0)
    
    # Handle near-zero std to avoid division by zero
    std = np.where(std < 1e-6, 1.0, std)
    
    # Compute sparsity (percentage of zeros)
    zero_mask = np.abs(X) < 1e-6
    sparsity = np.mean(zero_mask) * 100
    print(f"Data sparsity: {sparsity:.2f}% near-zero values")
    
    # Check for skewed features that might benefit from log transform
    skewness = {}
    for i in range(X.shape[1]):
        # Only consider features with non-negative values for log transform
        feature_data = X[:, i]
        if np.all(feature_data >= 0) and np.std(feature_data) > 0:
            # Calculate skewness - values > 2 are highly skewed
            feature_skew = np.mean(((feature_data - np.mean(feature_data)) / np.std(feature_data)) ** 3)
            if abs(feature_skew) > 2.0:
                skewness[feature_names[i]] = feature_skew
    
    if skewness:
        print(f"Found {len(skewness)} highly skewed features that might benefit from log transformation.")
        print("Top 5 most skewed features:")
        for feature, skew in sorted(skewness.items(), key=lambda x: abs(x[1]), reverse=True)[:5]:
            print(f"  {feature}: skewness = {skew:.2f}")
    
    # Create feature statistics for better initialization
    feature_stats = {
        'mean': mean,
        'std': std,
        'min': np.min(X, axis=0),
        'max': np.max(X, axis=0),
        'sparsity': np.mean(zero_mask, axis=0) * 100,  # Per-feature sparsity
    }
    
    # Optional: Apply Z-score normalization before returning
    X_normalized = (X - mean) / std
    
    # Clip normalized values to a reasonable range to avoid exploding gradients
    X_normalized = np.clip(X_normalized, -10, 10)
    
    # Final check for any remaining NaNs or infs after all processing
    if np.any(~np.isfinite(X_normalized)):
        print("Warning: Non-finite values still present after preprocessing. Fixing...")
        X_normalized = np.nan_to_num(X_normalized, nan=0.0, posinf=10.0, neginf=-10.0)
    
    print(f"Preprocessing complete. Output shape: {X_normalized.shape}")
    return X_normalized, feature_names, feature_stats


def train_autoencoder(X, feature_stats, n_epochs=300, batch_size=512, 
                     lr=1e-3, bottleneck_dim=89, 
                     weight_decay=1e-4, dropout_rate=0.2) -> ImprovedAutoencoder:
    """Train the improved fusion autoencoder."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Initialize model with feature statistics for better scale initialization
    model = ImprovedAutoencoder(
        X.shape[1], 
        bottleneck_dim=bottleneck_dim, 
        dropout_rate=dropout_rate,
        feature_stats=feature_stats
    ).to(device)
    
    # Use AdamW optimizer for better weight decay handling
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    
    # Learning rate scheduler with cosine annealing
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=50, T_mult=2, eta_min=1e-6
    )
    
    # Loss function - MSE for reconstruction
    criterion = nn.MSELoss()
    
    # Convert data to float32 and normalize
    X = X.astype(np.float32)
    mean = np.mean(X, axis=0, keepdims=True)
    std = np.std(X, axis=0, keepdims=True)
    std[std == 0] = 1  # Avoid division by zero
    X = (X - mean) / std
    
    # Create train/val split
    val_size = int(0.1 * len(X))
    indices = np.random.permutation(len(X))
    train_indices = indices[val_size:]
    val_indices = indices[:val_size]
    
    train_dataset = TensorDataset(torch.tensor(X[train_indices]))
    val_dataset = TensorDataset(torch.tensor(X[val_indices]))
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    print(f"\nTraining improved fusion autoencoder:")
    print(f"- Input features: {X.shape[1]}")
    print(f"- Bottleneck size: {bottleneck_dim}")
    print(f"- Compression ratio: {X.shape[1]/bottleneck_dim:.2f}x")
    print(f"- Training samples: {len(train_dataset)}")
    print(f"- Validation samples: {len(val_dataset)}")
    print(f"- Batch size: {batch_size}")
    print(f"- Dropout rate: {dropout_rate}")
    print(f"- Initial learning rate: {lr}")
    print(f"- Weight decay: {weight_decay}\n")
    
    best_val_loss = float('inf')
    best_model_state = None
    patience = 30
    patience_counter = 0
    train_losses = []
    val_losses = []
    
    start_time = time.time()
    for epoch in range(n_epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        for (batch,) in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            recon = model(batch)
            loss = criterion(recon, batch)
            loss.backward()
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * batch.size(0)
        
        train_loss /= len(train_dataset)
        train_losses.append(train_loss)
        
        # Update learning rate
        scheduler.step()
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for (batch,) in val_loader:
                batch = batch.to(device)
                recon = model(batch)
                loss = criterion(recon, batch)
                val_loss += loss.item() * batch.size(0)
        
        val_loss /= len(val_dataset)
        val_losses.append(val_loss)
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
        
        # Early stopping
        if patience_counter >= patience:
            print(f"\nEarly stopping triggered after {epoch+1} epochs")
            break
        
        # Print progress
        if epoch % 10 == 0 or epoch == n_epochs - 1:
            elapsed = time.time() - start_time
            current_lr = scheduler.get_last_lr()[0]
            print(f"Epoch {epoch+1}/{n_epochs} [{elapsed:.0f}s]")
            print(f"Train Loss: {train_loss:.6f}")
            print(f"Val Loss: {val_loss:.6f}")
            print(f"Best Val Loss: {best_val_loss:.6f}")
            print(f"Learning Rate: {current_lr:.2e}")
            print("-" * 50)
    
    # Restore best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    # Save normalization parameters with the model
    model.register_buffer('data_mean', torch.tensor(mean.squeeze()))
    model.register_buffer('data_std', torch.tensor(std.squeeze()))
    
    # Print final training time
    total_time = time.time() - start_time
    print(f"\nTraining completed in {total_time:.0f} seconds ({total_time/60:.1f} minutes)")
    
    return model, {'train_losses': train_losses, 'val_losses': val_losses}


def evaluate_model(model, X, feature_names):
    """Evaluate model performance with detailed metrics."""
    device = next(model.parameters()).device
    model.eval()
    
    # Normalize input data
    X = X.astype(np.float32)
    X = (X - model.data_mean.cpu().numpy()) / model.data_std.cpu().numpy()
    X_tensor = torch.tensor(X, dtype=torch.float32).to(device)
    
    with torch.no_grad():
        # Get bottleneck representations
        bottleneck = model.encode(X_tensor)
        # Get reconstructions
        recon = model(X_tensor)
        
        # Denormalize
        recon = recon.cpu().numpy() * model.data_std.cpu().numpy() + model.data_mean.cpu().numpy()
        X = X * model.data_std.cpu().numpy() + model.data_mean.cpu().numpy()
        
        # Calculate metrics
        mse = np.mean((X - recon) ** 2)
        mae = np.mean(np.abs(X - recon))
        
        # Calculate feature-wise metrics
        feature_metrics = []
        for i, name in enumerate(feature_names):
            metrics = {
                'name': name,
                'mse': np.mean((X[:, i] - recon[:, i]) ** 2),
                'mae': np.mean(np.abs(X[:, i] - recon[:, i])),
                'max_error': np.max(np.abs(X[:, i] - recon[:, i])),
                'r2': 1 - np.sum((X[:, i] - recon[:, i]) ** 2) / np.sum((X[:, i] - np.mean(X[:, i])) ** 2)
            }
            feature_metrics.append(metrics)
        
        # Calculate bottleneck statistics
        bottleneck = bottleneck.cpu().numpy()
        bottleneck_stats = {
            'mean': np.mean(bottleneck),
            'std': np.std(bottleneck),
            'active_dims': np.mean(np.abs(bottleneck) > 0.1, axis=0).sum(),
            'total_dims': bottleneck.shape[1]
        }
        
        # Print results
        print("\nModel Evaluation:")
        print(f"Overall MSE: {mse:.6f}")
        print(f"Overall MAE: {mae:.6f}")
        
        print("\nBottleneck Analysis:")
        print(f"- Dimensions: {bottleneck_stats['total_dims']}")
        print(f"- Active dimensions: {bottleneck_stats['active_dims']:.1f}")
        print(f"- Mean activation: {bottleneck_stats['mean']:.4f}")
        print(f"- Activation std: {bottleneck_stats['std']:.4f}")
        
        print("\nTop 10 Best Reconstructed Features:")
        sorted_metrics = sorted(feature_metrics, key=lambda x: x['r2'], reverse=True)
        for metrics in sorted_metrics[:10]:
            print(f"{metrics['name']:<30} R²: {metrics['r2']:>8.4f} MSE: {metrics['mse']:>10.4f}")
        
        print("\nTop 10 Worst Reconstructed Features:")
        for metrics in sorted_metrics[-10:]:
            print(f"{metrics['name']:<30} R²: {metrics['r2']:>8.4f} MSE: {metrics['mse']:>10.4f}")
        
        return {
            'mse': mse,
            'mae': mae,
            'feature_metrics': feature_metrics,
            'bottleneck_stats': bottleneck_stats
        }


def save_model(model, feature_names, model_path='models/fusion_autoencoder.pt'):
    """Save the trained model and its metadata."""
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # Create a checkpoint with model weights and metadata
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'input_size': model.encoder[0].in_features,  # Get input size from first encoder layer
        'bottleneck_size': model.bottleneck_dim,
        'feature_names': feature_names
    }
    
    # Save the checkpoint
    torch.save(checkpoint, model_path)
    print(f"Model saved to {model_path}")


def main():
    """Main training function with all improvements."""
    N_ROWS_SAMPLE = 50000  # Sample size
    N_FX_PAIRS = 20  # As per PAIRS_BY_LIQUIDITY_OANDA
    N_ETF_SYMBOLS = 34  # As per specification
    
    # Hyperparameters
    bottleneck_dim = 89  # 89-dimensional bottleneck
    batch_size = 512  # Larger batch size for faster training
    n_epochs = 300  # More epochs with early stopping for robustness
    dropout_rate = 0.2  # Dropout rate for regularization
    
    print("Fetching selected features for all instruments...")
    instrument_to_features_map = get_selected_features_per_instrument()
    
    # Validate data quality across instruments
    validation_results = validate_data_quality(instrument_to_features_map)
    
    fx_pairs = PAIRS_BY_LIQUIDITY_OANDA[:N_FX_PAIRS]
    
    etf_symbols = []
    all_db_instruments = sorted(list(instrument_to_features_map.keys()))
    for inst in all_db_instruments:
        if inst not in fx_pairs:
            etf_symbols.append(inst)
    etf_symbols = etf_symbols[:N_ETF_SYMBOLS]
    
    print(f"Target FX pairs ({len(fx_pairs)}): {fx_pairs}")
    print(f"Target ETF symbols ({len(etf_symbols)}): {etf_symbols}")
    
    # Fix for feature naming convention issue
    print("\nValidating feature naming conventions in the database...")
    has_prefixes = verify_feature_naming_in_db(instrument_to_features_map)
    print(f"Database uses {'prefixed' if has_prefixes else 'non-prefixed'} feature naming convention")

    print("\nLoading Forex data...")
    df_fx, fx_feature_names = load_instrument_data(
        target_instruments=fx_pairs,
        instrument_feature_map=instrument_to_features_map,
        table_name='forex_features',
        n_rows=N_ROWS_SAMPLE,
        check_for_prefix=True  # Enable prefix check
    )
    
    print("\nLoading ETF data...")
    df_etf, etf_feature_names = load_instrument_data(
        target_instruments=etf_symbols,
        instrument_feature_map=instrument_to_features_map,
        table_name='etf_features',
        n_rows=N_ROWS_SAMPLE,
        check_for_prefix=True  # Enable prefix check
    )
    
    if df_fx is None or df_fx.empty or df_etf is None or df_etf.empty:
        print("Critical error: FX or ETF data loading failed or returned empty. Exiting.")
        return
    
    # Normalize timestamps to date for proper daily alignment
    print("Normalizing FX and ETF timestamps to midnight for daily alignment...")
    if not df_fx.empty:
        df_fx.index = df_fx.index.normalize()
    if not df_etf.empty:
        df_etf.index = df_etf.index.normalize()
    
    # Align FX and ETF data by timestamp (outer join to keep all timestamps)
    print(f"\nAligning FX (shape {df_fx.shape}) and ETF (shape {df_etf.shape}) data by timestamp...")
    df_combined = pd.merge(df_fx, df_etf, left_index=True, right_index=True, how='outer')
    
    if df_combined.empty:
        print("Critical error: Combined FX and ETF data is empty after timestamp alignment. Exiting.")
        print(f"FX timestamps example: {df_fx.index[:5].tolist() if not df_fx.empty else 'N/A'}")
        print(f"ETF timestamps example: {df_etf.index[:5].tolist() if not df_etf.empty else 'N/A'}")
        return
    
    print(f"Aligned combined data shape: {df_combined.shape}")
    
    # Forward fill missing values (for holidays/weekends)
    print("Forward filling missing values for holidays/weekends...")
    df_combined = df_combined.fillna(method='ffill')
    
    # Backward fill any remaining NaNs at the start
    df_combined = df_combined.fillna(method='bfill')
    
    # Replace any remaining NaNs with 0
    df_combined = df_combined.fillna(0)
    
    # Validate data quality
    print("\nValidating combined data quality...")
    nan_counts = df_combined.isna().sum()
    if nan_counts.any():
        print("Warning: NaN values found after filling:")
        print(nan_counts[nan_counts > 0])
    
    # Check for infinite values
    inf_counts = np.isinf(df_combined.values).sum(axis=0)
    if inf_counts.any():
        print("Warning: Infinite values found:")
        inf_cols = df_combined.columns[inf_counts > 0]
        print(f"Columns with inf values: {inf_cols.tolist()}")
        # Replace inf values with large finite numbers
        df_combined = df_combined.replace([np.inf, -np.inf], [1e9, -1e9])
    
    X = df_combined.values.astype(np.float32)
    feature_names = df_combined.columns.tolist()
    
    if X.shape[0] == 0:
        print("Critical error: No data rows after processing. Exiting.")
        return
    
    print(f"\nTotal features for AE: {X.shape[1]}")
    print(f"Total samples for AE: {X.shape[0]}")
    
    # Print input statistics to verify data quality
    print_input_stats(X, feature_names)
    
    # Apply preprocessing to improve data quality
    print("\nApplying data preprocessing...")
    X_processed, feature_names_processed, feature_stats = preprocess_data(X, feature_names)
    
    # Train model with improved parameters
    model, training_history = train_autoencoder(
        X_processed, 
        feature_stats=feature_stats,
        n_epochs=n_epochs, 
        batch_size=batch_size, 
        bottleneck_dim=bottleneck_dim, 
        dropout_rate=dropout_rate
    )
    
    # Evaluate model
    evaluation_metrics = evaluate_model(model, X_processed, feature_names_processed)
    
    # Save model
    save_model(model, feature_names_processed)
    
    print("\nTraining completed successfully!")
    print(f"Model saved with {bottleneck_dim}-dimensional bottleneck")


if __name__ == "__main__":
    main() 