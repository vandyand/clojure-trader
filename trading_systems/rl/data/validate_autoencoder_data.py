#!/usr/bin/env python
"""
Validate the input data for the fusion autoencoder without training.
This script loads a small sample of data and checks for quality issues.
"""
import os
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add the parent directory to Python path to access rl module
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data.autoencoder_fusion import get_conn, get_selected_features_per_instrument

def validate_raw_data():
    """Check raw feature values directly from the database for a single instrument."""
    print("Validating raw data for a single instrument...\n")
    
    # Connect to database
    conn = get_conn()
    cursor = conn.cursor()
    
    # Check forex_features table for a single instrument
    instrument = PAIRS_BY_LIQUIDITY_OANDA[0]  # e.g., EUR_USD
    print(f"Checking raw data for {instrument}...")
    
    # First, get the feature names for this instrument
    feature_map = get_selected_features_per_instrument()
    if instrument not in feature_map:
        print(f"Error: {instrument} not found in selected features!")
        return
    
    features = feature_map[instrument]
    print(f"Selected features ({len(features)}): {features[:5]}...")
    
    # Query one row directly to see raw feature values
    query = f"""
    SELECT timestamp, features 
    FROM forex_features 
    WHERE instrument = '{instrument}' AND granularity = 'D'
    ORDER BY timestamp DESC
    LIMIT 5
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    for timestamp, features_json in rows:
        print(f"\nTimestamp: {timestamp}")
        print("Raw features (JSON):")
        for key, value in features_json.items():
            print(f"{key}: {value} (type: {type(value).__name__})")
    
    # Now check for zeros and NaNs in the selected features
    placeholders = ", ".join([f"features->>'{f}'" for f in features[:5]])
    query = f"""
    SELECT timestamp, {placeholders}
    FROM forex_features
    WHERE instrument = '{instrument}' AND granularity = 'D'
    ORDER BY timestamp DESC
    LIMIT 20
    """
    
    # Get the results as a pandas DataFrame for easier analysis
    df = pd.read_sql_query(query, conn)
    
    # Basic statistics
    print("\nStatistics for extracted features:")
    print(df.describe())
    
    # Check for zeros
    zero_counts = (df == 0).sum()
    print("\nZero counts per feature:")
    print(zero_counts)
    
    # Check for NaNs
    nan_counts = df.isna().sum()
    print("\nNaN counts per feature:")
    print(nan_counts)
    
    # Close connection
    conn.close()

def check_input_transformation():
    """Check how the inputs are being transformed in the autoencoder pipeline."""
    from rl.data.autoencoder_fusion import load_instrument_data
    
    print("\nChecking input transformation for a small dataset...")
    
    # Get selected features
    instrument_features = get_selected_features_per_instrument()
    
    # Sample just 3 instruments
    sample_instruments = PAIRS_BY_LIQUIDITY_OANDA[:3]
    
    # Load a very small sample
    df, feature_names = load_instrument_data(
        target_instruments=sample_instruments,
        instrument_feature_map=instrument_features,
        table_name='forex_features',
        n_rows=10  # Just 10 rows for quick validation
    )
    
    if df is None or df.empty:
        print("Error: No data loaded!")
        return
    
    # Show the raw data
    print("\nRaw data sample (first 3 rows, first 5 columns):")
    print(df.iloc[:3, :5])
    
    # Compute basic statistics
    print("\nBasic statistics:")
    print(f"Data shape: {df.shape}")
    print(f"Non-zero values: {(df != 0).sum().sum()} of {df.size} ({(df != 0).sum().sum()/df.size*100:.2f}%)")
    
    # Check value ranges
    print("\nValue ranges per column (first 5 columns):")
    for col in df.columns[:5]:
        non_zero_values = df[col][df[col] != 0]
        if len(non_zero_values) > 0:
            print(f"{col}: min={non_zero_values.min():.4f}, max={non_zero_values.max():.4f}, mean={non_zero_values.mean():.4f}")
        else:
            print(f"{col}: ALL ZEROS")
    
    # Count unique values
    print("\nUnique value counts (first 5 columns):")
    for col in df.columns[:5]:
        unique_vals = df[col].nunique()
        print(f"{col}: {unique_vals} unique values")

if __name__ == "__main__":
    print("Data Validation for Fusion Autoencoder\n")
    validate_raw_data()
    check_input_transformation() 