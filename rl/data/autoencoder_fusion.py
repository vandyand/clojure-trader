import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import time
import os
from typing import List, Tuple, Dict, Optional
import pandas as pd
from pathlib import Path
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
import psycopg2
import re # For sanitizing SQL aliases
from sklearn.preprocessing import RobustScaler

# Database connection (ensure these are defined or imported, e.g., from a config.py)
DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

def get_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

# Helper function to create safe SQL aliases for instrument names
def sanitize_sql_alias(instrument_name: str) -> str:
    # Replace non-alphanumeric characters with underscore
    return re.sub(r'[^a-zA-Z0-9_]', '_', instrument_name)

# Scaled tanh input layer
class ScaledTanhInput(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))
    
    def forward(self, x):
        return torch.tanh(self.scale * x + self.bias)

class Autoencoder(nn.Module):
    def __init__(self, n_features, bottleneck_dim=64):  # Reduced bottleneck dimension
        super().__init__()
        # Define layer sizes with progressive compression
        self.bottleneck_dim = bottleneck_dim
        hidden_dim1 = n_features // 2
        hidden_dim2 = n_features // 4
        
        # Input scaling layer
        self.input_layer = ScaledTanhInput(n_features)
        
        # Encoder layers with LeakyReLU activation
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Linear(hidden_dim2, bottleneck_dim),
            nn.Tanh(),  # Keep tanh in bottleneck for bounded representation
            nn.BatchNorm1d(bottleneck_dim)
        )
        
        # Decoder layers with LeakyReLU activation
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Linear(hidden_dim2, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
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

def get_selected_features_per_instrument() -> Dict[str, List[str]]:
    """
    Returns a dictionary mapping instrument to a list of 23 selected features from selected_features_per_instrument table.
    Validates that each instrument has exactly 23 selected features.
    """
    # Implementing with a raw query to have more control over the output format
    instrument_features = {}
    with get_conn() as conn:
        query = """
        SELECT instrument, feature_name 
        FROM selected_features_per_instrument 
        ORDER BY instrument, rank
        """
        with conn.cursor() as cur:
            cur.execute(query)
            for row in cur:
                instrument, feature_name = row
                if instrument not in instrument_features:
                    instrument_features[instrument] = []
                # Ensure only 23 features are added if more are present for some reason, though query implies rank handles this
                if len(instrument_features[instrument]) < 23:
                    instrument_features[instrument].append(feature_name)
    # Validate that all instruments have 23 features
    for instrument, features in instrument_features.items():
        if len(features) != 23:
            print(f"Warning: Instrument {instrument} has {len(features)} features, expected 23.")
    return instrument_features

def verify_feature_naming_in_db(instrument_features_map):
    """
    Verify if features in the database include instrument prefixes or not.
    This function checks a sample of data to determine the naming convention.
    
    Args:
        instrument_features_map: Dictionary mapping instruments to their features
    
    Returns:
        bool: True if features have instrument prefixes, False otherwise
    """
    # Take a sample instrument
    sample_instruments = list(instrument_features_map.keys())[:2]
    if not sample_instruments:
        print("Warning: No instruments found in feature map")
        return False
    
    has_prefixes = False
    
    with get_conn() as conn:
        # Check forex_features table
        try:
            for instrument in sample_instruments:
                # Check both with and without prefix for a single feature
                feature = instrument_features_map[instrument][0]
                prefixed_feature = f"{instrument}__{feature}"
                
                # Query for the feature with prefix
                prefix_query = f"""
                SELECT COUNT(*) FROM forex_features 
                WHERE features->>'%s' IS NOT NULL LIMIT 1
                """ % prefixed_feature
                
                with conn.cursor() as cur:
                    cur.execute(prefix_query)
                    prefix_count = cur.fetchone()[0]
                
                # Query for the feature without prefix
                no_prefix_query = f"""
                SELECT COUNT(*) FROM forex_features 
                WHERE features->>'%s' IS NOT NULL LIMIT 1
                """ % feature
                
                with conn.cursor() as cur:
                    cur.execute(no_prefix_query)
                    no_prefix_count = cur.fetchone()[0]
                
                if prefix_count > 0:
                    print(f"Features with instrument prefix exist in database (e.g., '{prefixed_feature}')")
                    has_prefixes = True
                    break
                elif no_prefix_count > 0:
                    print(f"Features without instrument prefix exist in database (e.g., '{feature}')")
                    has_prefixes = False
                    break
        except Exception as e:
            print(f"Error checking feature naming convention: {e}")
    
    return has_prefixes

def load_instrument_data(
    target_instruments: List[str], 
    instrument_feature_map: Dict[str, List[str]],
    table_name: str, # 'forex_features' or 'etf_features'
    n_rows: int = 50000,
    max_instruments_in_query: int = 10, # To avoid overly complex SQL queries
    check_for_prefix: bool = False # Check if features have instrument prefixes
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Loads data for a list of instruments from the specified table, ensuring 23 features each,
    and aligns them by timestamp. Fetches data in chunks of instruments if needed.
    Returns a Pandas DataFrame (timestamps as index, columns as instrument_feature) and a list of all feature names.
    """
    all_instrument_dfs = []
    all_feature_names_ordered = []
    
    # Determine if features have instrument prefixes in the database
    features_have_prefixes = False
    if check_for_prefix:
        try:
            # Sample check to detect if prefixes are used
            with get_conn() as conn:
                sample_instrument = target_instruments[0]
                sample_feature = instrument_feature_map[sample_instrument][0]
                prefixed_feature = f"{sample_instrument}__{sample_feature}"
                
                # Try with prefix
                prefix_query = f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE features->>'%s' IS NOT NULL LIMIT 1
                """ % prefixed_feature
                prefix_count = pd.read_sql_query(prefix_query, conn).iloc[0, 0]
                
                # Try without prefix
                no_prefix_query = f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE features->>'%s' IS NOT NULL LIMIT 1
                """ % sample_feature
                no_prefix_count = pd.read_sql_query(no_prefix_query, conn).iloc[0, 0]
                
                features_have_prefixes = prefix_count > 0
                
                if features_have_prefixes:
                    print(f"Features in {table_name} use instrument prefixes (e.g., '{prefixed_feature}')")
                else:
                    print(f"Features in {table_name} do NOT use instrument prefixes (e.g., '{sample_feature}')")
        except Exception as e:
            print(f"Warning: Could not determine feature prefix format: {e}")
            print("Proceeding with default behavior (assuming no prefixes)")
    
    # Process instruments in chunks to keep SQL manageable
    for i in range(0, len(target_instruments), max_instruments_in_query):
        chunk_instruments = target_instruments[i:i+max_instruments_in_query]
        if not chunk_instruments:
            continue

        select_clauses = []
        instrument_specific_feature_names_ordered = []

        for instrument_name in chunk_instruments:
            if instrument_name not in instrument_feature_map or len(instrument_feature_map[instrument_name]) != 23:
                print(f"Skipping {instrument_name} from {table_name}: missing in map or does not have 23 features.")
                continue
            
            features_for_instrument = instrument_feature_map[instrument_name]
            for feature_name in features_for_instrument:
                # Standardized column name: EUR_USD__feature_name
                col_alias = f"{instrument_name}__{feature_name}"
                # Table alias for the current instrument, sanitized
                current_instrument_sql_alias = sanitize_sql_alias(instrument_name)
                
                # If features have prefixes in the database, use the prefixed feature name
                # Otherwise use the base feature name
                feature_key = feature_name
                if features_have_prefixes:
                    feature_key = col_alias
                
                select_clauses.append(f"t_{current_instrument_sql_alias}.features->>'{feature_key}' AS \"{col_alias}\"")
                instrument_specific_feature_names_ordered.append(col_alias)
        
        if not select_clauses: # No valid instruments in this chunk
            continue

        # Use the first instrument in the chunk as the base for joins
        # Sanitize the base instrument name for its SQL alias
        base_instrument_name_sanitized = sanitize_sql_alias(chunk_instruments[0])
        base_instrument_sql_alias = f"t_{base_instrument_name_sanitized}" 
        
        join_clauses = []
        for instrument_name_to_join in chunk_instruments[1:]: # Join other instruments in the chunk to the base
             if instrument_name_to_join not in instrument_feature_map or len(instrument_feature_map[instrument_name_to_join]) != 23:
                continue # Already warned
             # Sanitize the instrument name for its SQL alias in the JOIN clause
             instrument_to_join_sql_alias = sanitize_sql_alias(instrument_name_to_join)
             join_clauses.append(
                f"INNER JOIN {table_name} t_{instrument_to_join_sql_alias} "
                f"ON t_{instrument_to_join_sql_alias}.timestamp = {base_instrument_sql_alias}.timestamp "
                f"AND t_{instrument_to_join_sql_alias}.instrument = '{instrument_name_to_join}'" 
                f" AND t_{instrument_to_join_sql_alias}.granularity = 'D'" 
            )

        sql_query = f"""
        SELECT
            {base_instrument_sql_alias}.timestamp AS "timestamp",
            {", ".join(select_clauses)}
        FROM {table_name} {base_instrument_sql_alias}
        {" ".join(join_clauses)}
        WHERE {base_instrument_sql_alias}.instrument = '{chunk_instruments[0]}'
        AND {base_instrument_sql_alias}.granularity = 'D'
        ORDER BY {base_instrument_sql_alias}.timestamp DESC
        LIMIT {n_rows} 
        """
        # LIMIT n_rows here is tricky; it limits based on the base instrument's available rows.
        # A more robust approach might be to fetch all, then sample, or sample timestamps first.
        # For now, keeping it simpler. Consider revising if data diversity is an issue.

        try:
            with get_conn() as conn:
                chunk_df = pd.read_sql_query(sql_query, conn)
            
            if chunk_df.empty:
                print(f"Warning: No data returned for chunk starting with {chunk_instruments[0]} from {table_name}.")
                
                # *** Fix for issue with prefixes: Try the alternative prefix approach if we get empty results ***
                if check_for_prefix:
                    print(f"Attempting to query with {'prefixed' if not features_have_prefixes else 'non-prefixed'} feature names...")
                    # Toggle the features_have_prefixes flag and retry
                    features_have_prefixes = not features_have_prefixes
                    # Reset and try again with new chunk
                    i -= max_instruments_in_query  # Move back to retry this chunk
                    continue
            
            # Debug raw data values
            print(f"\nRaw data sample for first 5 rows from {chunk_instruments[0]}:")
            raw_sample = chunk_df.head(3)
            print(raw_sample)
            
            # Check for non-numeric values
            non_numeric_cols = []
            for col in chunk_df.columns:
                if col != 'timestamp':
                    try:
                        pd.to_numeric(chunk_df[col])
                    except:
                        non_numeric_cols.append(col)
                        print(f"Column {col} contains non-numeric values. Examples: {chunk_df[col].dropna().head(3).values}")
            
            # Convert non-numeric columns to numeric, coercing errors to NaN
            for col in non_numeric_cols:
                print(f"Converting column {col} to numeric...")
                chunk_df[col] = pd.to_numeric(chunk_df[col], errors='coerce')

            # Attempt to convert to UTC then make naive to handle potential timezone issues
            try:
                chunk_df['timestamp'] = pd.to_datetime(chunk_df['timestamp'], utc=True).dt.tz_localize(None)
            except Exception as e_tz:
                print(f"Warning: Timestamp conversion to UTC failed for chunk {chunk_instruments[0]}: {e_tz}. Attempting direct conversion.")
                # Fallback or alternative conversion if direct UTC fails (e.g., if already naive or different issue)
                chunk_df['timestamp'] = pd.to_datetime(chunk_df['timestamp'])
            
            chunk_df = chunk_df.set_index('timestamp')
            # Count NaN values before filling
            nan_counts = chunk_df.isna().sum()
            if nan_counts.any():
                print(f"NaN values found before filling: {sum(nan_counts)}")
                print(f"Columns with most NaNs: {nan_counts.nlargest(5).to_dict()}")
            
            # First try to fill NaNs with near neighbors (LOCF method)
            chunk_df = chunk_df.fillna(method='ffill').fillna(method='bfill')
            
            # Only fill remaining NaNs with 0 
            remaining_nans = chunk_df.isna().sum().sum()
            if remaining_nans > 0:
                print(f"Filling {remaining_nans} remaining NaNs with 0")
                chunk_df = chunk_df.fillna(0)
            
            # Report on zero values
            zero_counts = (chunk_df == 0).sum()
            if zero_counts.any():
                print(f"Columns with most zeros: {zero_counts.nlargest(5).to_dict()}")
                zero_pct = ((chunk_df == 0).sum() / len(chunk_df) * 100).mean()
                print(f"Average percentage of zeros across columns: {zero_pct:.2f}%")
            
            # Convert to float32 for efficiency
            chunk_df = chunk_df.astype(np.float32) 
            all_instrument_dfs.append(chunk_df)
            all_feature_names_ordered.extend(instrument_specific_feature_names_ordered)
            print(f"Loaded data for instruments: {chunk_instruments} from {table_name} - Shape: {chunk_df.shape}")

        except Exception as e:
            print(f"Error loading data for chunk {chunk_instruments} from {table_name}: {e}")
            print(f"SQL Query: {sql_query}")
            continue

    if not all_instrument_dfs:
        print(f"No data loaded for target instruments from {table_name}.")
        return None, []

    # Concatenate dataframes from all chunks; they should align by timestamp due to separate queries and then outer merge.
    # However, a simple concat might be problematic if timestamps aren't perfectly overlapping across chunks.
    # A more robust way is to merge them all on timestamp.
    if len(all_instrument_dfs) == 1:
        final_df = all_instrument_dfs[0]
    else:
        final_df = all_instrument_dfs[0]
        for i in range(1, len(all_instrument_dfs)):
            # Using outer join to keep all timestamps, then we'll handle NaNs
            final_df = pd.merge(final_df, all_instrument_dfs[i], on='timestamp', how='outer', suffixes=(None, f'_dup{i}'))
            # Handle potential duplicate columns if any (shouldn't happen with good aliases)
            final_df = final_df.loc[:,~final_df.columns.duplicated()]


    # Sort by timestamp just in case
    final_df = final_df.sort_index()
    
    # After all merges, fill any NaNs that arose from outer joins (timestamps not present in all chunks)
    # This fillna is critical after merges.
    final_df = final_df.fillna(0).astype(np.float32)

    # Ensure the column order matches all_feature_names_ordered
    # Some features might be missing if an instrument chunk failed completely
    # Reindex to ensure consistent column order and presence, filling missing ones with 0
    final_df = final_df.reindex(columns=all_feature_names_ordered, fill_value=0.0).astype(np.float32)

    return final_df, all_feature_names_ordered

def fetch_fx_features() -> List[str]:
    """Fetch selected features from forex data."""
    # This function is now replaced by the logic in main() using get_selected_features_per_instrument
    # and load_instrument_data. Keeping for API compatibility if anything else calls it, but it's not used by main.
    print("Warning: fetch_fx_features() is deprecated for autoencoder_fusion.py's main data loading.")
    return []

def fetch_etf_features() -> List[str]:
    """Fetch selected features from ETF data."""
    # This function is now replaced by the logic in main() using get_selected_features_per_instrument
    # and load_instrument_data. Keeping for API compatibility.
    print("Warning: fetch_etf_features() is deprecated for autoencoder_fusion.py's main data loading.")
    return []

def generate_synthetic_data(n_rows: int, n_features: int, scale: float = 1.0, sparsity: float = 0.1) -> np.ndarray:
    """Generate synthetic data with similar properties to financial time series."""
    # This function will no longer be used by the main data loading pipeline.
    # Kept for potential testing or other uses.
    # Base random normal distribution
    X = np.random.randn(n_rows, n_features) * scale
    
    # Add some trends (random walk component)
    trends = np.cumsum(np.random.randn(n_rows, n_features) * 0.1, axis=0)
    X += trends
    
    # Add some seasonality
    t = np.linspace(0, 4*np.pi, n_rows)
    seasonality = np.outer(np.sin(t), np.random.randn(n_features))
    X += seasonality * scale * 0.5
    
    # Add some sparsity (set random values to 0)
    mask = np.random.random(X.shape) < sparsity
    X[mask] = 0
    
    # Add some outliers
    outlier_mask = np.random.random(X.shape) < 0.01
    X[outlier_mask] *= 10
    
    return X

def load_fx_data(n_rows: int = 50000) -> Tuple[np.ndarray, List[str]]:
    """Load forex data with selected features."""
    # This function is now replaced by the logic in main() using get_selected_features_per_instrument
    # and load_instrument_data. It will not be directly called by the new main logic.
    # Returning empty data to signify deprecation if accidentally called.
    print("Warning: load_fx_data() is deprecated. Use new data loading in main().")
    return np.array([]), []

def load_etf_data(n_rows: int = 50000) -> Tuple[np.ndarray, List[str]]:
    """Load ETF data with selected features."""
    # This function is now replaced by the logic in main() using get_selected_features_per_instrument
    # and load_instrument_data. It will not be directly called by the new main logic.
    # Returning empty data to signify deprecation if accidentally called.
    print("Warning: load_etf_data() is deprecated. Use new data loading in main().")
    return np.array([]), []

def print_input_stats(X: np.ndarray, feature_names: List[str]):
    """Print statistics about input features."""
    print("\nInput feature statistics:")
    for i, name in enumerate(feature_names):
        values = X[:, i]
        mean = np.mean(values)
        std = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)
        zero_pct = np.mean(values == 0) * 100
        print(f"{name:<30} mean={mean:>12.4f} std={std:>12.4f} min={min_val:>12.4f} max={max_val:>12.4f} %zero={zero_pct:>4.1f}")

def preprocess_data(X, feature_names):
    """Preprocess data to improve quality before training."""
    print("\nData preprocessing:")
    
    # Count zero values per feature before processing
    zero_counts = np.sum(X == 0, axis=0)
    print(f"Features with >90% zeros before preprocessing: {np.sum(zero_counts > 0.9 * X.shape[0])}")
    
    # 1. Remove constant features
    std_per_feature = np.std(X, axis=0)
    non_constant_mask = std_per_feature > 1e-6
    X = X[:, non_constant_mask]
    good_features = [f for i, f in enumerate(feature_names) if non_constant_mask[i]]
    print(f"Removed {np.sum(~non_constant_mask)} constant features")
    
    # 2. Apply mild scaling to prevent extreme values
    X_clipped = np.clip(X, -1e6, 1e6)  # Clip extreme values
    
    # 3. Add small noise to zero values to help training
    zero_mask = X_clipped == 0
    X_with_noise = X_clipped.copy()
    X_with_noise[zero_mask] = np.random.normal(0, 1e-4, size=np.sum(zero_mask))
    
    # 4. Use robust scaling (based on percentiles rather than mean/std)
    scaler = RobustScaler(quantile_range=(5, 95))
    X_scaled = scaler.fit_transform(X_with_noise)
    
    print(f"Data shape after preprocessing: {X_scaled.shape}")
    print(f"Features retained: {len(good_features)}")
    
    return X_scaled, good_features

def train_autoencoder(X: np.ndarray, n_epochs: int = 400, batch_size: int = 256, 
                     lr: float = 1e-3, bottleneck_dim: int = 149, 
                     weight_decay: float = 1e-4) -> Autoencoder:
    """Train the fusion autoencoder."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Initialize model
    model = Autoencoder(X.shape[1], bottleneck_dim).to(device)
    
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
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    print(f"\nTraining fusion autoencoder:")
    print(f"- Input features: {X.shape[1]}")
    print(f"- Bottleneck size: {bottleneck_dim}")
    print(f"- Compression ratio: {X.shape[1]/bottleneck_dim:.2f}x")
    print(f"- Training samples: {len(train_dataset)}")
    print(f"- Validation samples: {len(val_dataset)}")
    print(f"- Batch size: {batch_size}")
    print(f"- Initial learning rate: {lr}")
    print(f"- Weight decay: {weight_decay}\n")
    
    best_val_loss = float('inf')
    best_model_state = None
    patience = 50
    patience_counter = 0
    
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
            current_lr = scheduler.get_last_lr()[0]
            print(f"Epoch {epoch+1}/{n_epochs}")
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
    
    return model

def print_recon_examples(model: Autoencoder, X: np.ndarray, feature_names: List[str], n: int = 3):
    """Print reconstruction examples with detailed metrics."""
    device = next(model.parameters()).device
    model.eval()
    
    # Normalize input data
    X = X.astype(np.float32)
    X = (X - model.data_mean.cpu().numpy()) / model.data_std.cpu().numpy()
    X_tensor = torch.tensor(X[:n], dtype=torch.float32).to(device)
    
    with torch.no_grad():
        # Get bottleneck representation
        bottleneck = model.encode(X_tensor)
        # Get reconstruction
        recon = model(X_tensor)
        
        # Denormalize
        recon = recon.cpu().numpy() * model.data_std.cpu().numpy() + model.data_mean.cpu().numpy()
        X = X[:n] * model.data_std.cpu().numpy() + model.data_mean.cpu().numpy()
        
        # Print results
        print("\nReconstruction examples:")
        for i in range(n):
            print(f"\nSample {i+1}:")
            print(f"Bottleneck activation stats:")
            b = bottleneck[i].cpu().numpy()
            print(f"- Mean: {np.mean(b):.4f}")
            print(f"- Std: {np.std(b):.4f}")
            print(f"- Active dims: {np.sum(np.abs(b) > 0.1)}/{len(b)}")
            print("\nFeature comparisons:")
            for j, name in enumerate(feature_names):
                orig = X[i, j]
                rec = recon[i, j]
                err = abs(orig - rec)
                err_pct = (err / (abs(orig) + 1e-10)) * 100
                print(f"{name:<30} Orig: {orig:>10.4f} Recon: {rec:>10.4f} Err: {err:>10.4f} ({err_pct:>6.2f}%)")

def evaluate_model(model: Autoencoder, X: np.ndarray, feature_names: List[str]):
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

def save_model(model: Autoencoder, feature_names: List[str], save_dir: str = "models"):
    """Save model with feature information."""
    os.makedirs(save_dir, exist_ok=True)
    
    # Save model state
    model_path = os.path.join(save_dir, "fusion_autoencoder.pt")
    model_info = {
        'state_dict': model.state_dict(),
        'n_features': len(feature_names),
        'bottleneck_dim': model.bottleneck_dim,
        'feature_names': feature_names,
        'data_mean': model.data_mean.cpu().numpy(),
        'data_std': model.data_std.cpu().numpy()
    }
    torch.save(model_info, model_path)
    print(f"\nModel saved to {model_path}")

def main():
    """Main training function."""
    N_ROWS_SAMPLE = 50000 # Or make this an argparse argument
    N_FX_PAIRS = 20 # As per PAIRS_BY_LIQUIDITY_OANDA
    N_ETF_SYMBOLS = 34 # As per your spec

    print("Fetching selected features for all instruments...")
    instrument_to_features_map = get_selected_features_per_instrument()

    fx_pairs = PAIRS_BY_LIQUIDITY_OANDA[:N_FX_PAIRS]
    
    etf_symbols = []
    all_db_instruments = sorted(list(instrument_to_features_map.keys())) # Sort for consistent ordering
    for inst in all_db_instruments:
        if inst not in fx_pairs:
            etf_symbols.append(inst)
    etf_symbols = etf_symbols[:N_ETF_SYMBOLS] # Ensure we take only the specified number

    print(f"Target FX pairs ({len(fx_pairs)}): {fx_pairs}")
    print(f"Target ETF symbols ({len(etf_symbols)}): {etf_symbols}")

    print("\nLoading Forex data...")
    df_fx, fx_feature_names = load_instrument_data(
        target_instruments=fx_pairs,
        instrument_feature_map=instrument_to_features_map,
        table_name='forex_features',
        n_rows=N_ROWS_SAMPLE,  # n_rows applies per chunk query, consider total sample size strategy
        check_for_prefix=True
    )

    print("\nLoading ETF data...")
    df_etf, etf_feature_names = load_instrument_data(
        target_instruments=etf_symbols,
        instrument_feature_map=instrument_to_features_map,
        table_name='etf_features',
        n_rows=N_ROWS_SAMPLE,
        check_for_prefix=True
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
    df_combined = pd.merge(df_fx, df_etf, on='timestamp', how='outer')
    
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
    print("\nValidating data quality...")
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
    
    # The 'timestamp' index is currently the actual timestamp. For the AE, we just need the features.
    X = df_combined.values.astype(np.float32)
    # The feature_names list needs to correspond to the columns in df_combined (excluding timestamp if it was a column)
    # load_instrument_data already returns ordered feature names.
    # df_combined columns are already in order from fx_feature_names + etf_feature_names due to how merge and load_instrument_data work
    feature_names = fx_feature_names + etf_feature_names

    if X.shape[0] == 0:
        print("Critical error: No data rows after processing. Exiting.")
        return
    if X.shape[1] != (len(fx_pairs) * 23 + len(etf_symbols) * 23):
         print(f"Critical error: Number of features in X ({X.shape[1]}) does not match expected "
               f"({len(fx_pairs) * 23 + len(etf_symbols) * 23}). Exiting.")
         return

    print(f"\nTotal features for AE: {X.shape[1]}")
    print(f"Total samples for AE: {X.shape[0]}")
    
    # Print input statistics to verify data quality
    print_input_stats(X, feature_names)
    
    # Apply preprocessing to improve data quality
    print("\nApplying data preprocessing...")
    X, feature_names = preprocess_data(X, feature_names)
    
    # Train model with adjusted parameters
    model = train_autoencoder(X, n_epochs=200, batch_size=128, lr=5e-4, 
                            bottleneck_dim=64, weight_decay=1e-5)
    
    # Evaluate model
    evaluate_model(model, X, feature_names)
    
    # Print reconstruction examples
    print_recon_examples(model, X, feature_names, n=3)
    
    # Save model
    save_model(model, feature_names)

if __name__ == "__main__":
    main() 