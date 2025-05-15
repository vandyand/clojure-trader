#!/usr/bin/env python3
import os
import sys
import numpy as np
import pandas as pd
import json
import logging
from pathlib import Path

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("feature_adapter")

def load_etf_data(etf_file='etf_data/etf_summary.json'):
    """Load ETF data from file"""
    try:
        with open(etf_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading ETF data: {e}")
        return {}

def normalize_features(features):
    """Normalize a feature vector using z-score normalization"""
    mean = np.mean(features)
    std = np.std(features)
    if std == 0:
        return features  # Avoid division by zero
    return (features - mean) / std

def create_fixed_size_feature_vector(features_dict, expected_size=1084):
    """
    Create a feature vector with a fixed size for the model.
    
    Args:
        features_dict: Dictionary of features
        expected_size: Expected feature vector size required by the model
        
    Returns:
        Fixed-size numpy array
    """
    # Extract features into a flat list
    feature_list = []
    
    # Add features from each ETF
    for symbol, data in features_dict.items():
        feature_list.extend([
            data['last_price'],
            data['daily_change_pct'],
            data['ma_20'], 
            data['ma_50'],
            data['volatility']
        ])
    
    # Convert to numpy array
    feature_array = np.array(feature_list, dtype=np.float32)
    
    # Normalize features
    feature_array = normalize_features(feature_array)
    
    # Check if we need to adjust the size
    current_size = len(feature_array)
    logger.info(f"Current feature vector size: {current_size}, expected: {expected_size}")
    
    if current_size < expected_size:
        # Pad with zeros
        padding = np.zeros(expected_size - current_size, dtype=np.float32)
        feature_array = np.concatenate([feature_array, padding])
        logger.info(f"Padded feature vector from {current_size} to {expected_size}")
    elif current_size > expected_size:
        # Truncate
        feature_array = feature_array[:expected_size]
        logger.info(f"Truncated feature vector from {current_size} to {expected_size}")
    
    return feature_array

def get_adapted_feature_vector():
    """
    Create an adapted feature vector that matches the expected model input size.
    
    Returns:
        Numpy array with the expected shape
    """
    # Load ETF data
    etf_data = load_etf_data()
    
    # Create feature vector with fixed size
    feature_vector = create_fixed_size_feature_vector(etf_data)
    
    return feature_vector

if __name__ == "__main__":
    # Test the adapter
    feature_vector = get_adapted_feature_vector()
    print(f"Feature vector shape: {feature_vector.shape}")
    print(f"Sample of feature vector: {feature_vector[:10]}") 