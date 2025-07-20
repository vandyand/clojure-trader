"""
Feature engineering module for calculating technical indicators and other features.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

def calculate_features(df: pd.DataFrame, instrument: str, **kwargs) -> pd.DataFrame:
    """
    Calculate features for a price DataFrame
    
    Args:
        df: DataFrame with price data
        instrument: Instrument name
        **kwargs: Feature parameters
        
    Returns:
        DataFrame with calculated features
    """
    # Collect all features in a dictionary to avoid DataFrame fragmentation
    feature_dict = {}
    
    # Price-based features
    if kwargs.get('price_features', True):
        # Simple returns
        feature_dict[f"{instrument}__close_return"] = df["close"].pct_change()
        
        # Log returns
        feature_dict[f"{instrument}__close_log_return"] = np.log(df["close"] / df["close"].shift(1))
        
        # Price range
        feature_dict[f"{instrument}__high_low_range"] = (df["high"] - df["low"]) / df["close"]
        
        # Moving averages
        for period in kwargs.get('ma_periods', [3, 8, 21, 55, 144]):
            feature_dict[f"{instrument}__close_sma_{period}"] = df["close"].rolling(window=period).mean()
            feature_dict[f"{instrument}__close_ema_{period}"] = df["close"].ewm(span=period).mean()
        
        # Rate of change
        for period in kwargs.get('roc_periods', [1, 3, 8, 21, 55]):
            feature_dict[f"{instrument}__close_roc_{period}"] = df["close"].pct_change(periods=period)
        
        # Standard deviation
        for period in kwargs.get('std_periods', [5, 13, 21, 55]):
            feature_dict[f"{instrument}__close_std_{period}"] = df["close"].rolling(window=period).std()
        
        # Bollinger Bands
        for period in kwargs.get('bb_periods', [20]):
            mid = df["close"].rolling(window=period).mean()
            std = df["close"].rolling(window=period).std()
            feature_dict[f"{instrument}__close_bb_mid_{period}"] = mid
            feature_dict[f"{instrument}__close_bb_bbhi_{period}"] = (df["close"] - (mid + 2 * std)) / df["close"]
            feature_dict[f"{instrument}__close_bb_bblo_{period}"] = (df["close"] - (mid - 2 * std)) / df["close"]
        
        # RSI
        for period in kwargs.get('rsi_periods', [2, 8, 14]):
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss
            feature_dict[f"{instrument}__close_rsi_{period}"] = 100 - (100 / (1 + rs))
    
    # Volume-based features
    if 'volume' in df.columns and kwargs.get('volume_features', True):
        # Moving averages
        for period in kwargs.get('ma_periods', [3, 8, 21, 55, 144]):
            feature_dict[f"{instrument}__volume_sma_{period}"] = df["volume"].rolling(window=period).mean()
        
        # Rate of change
        for period in kwargs.get('roc_periods', [1, 3, 8, 21, 55]):
            feature_dict[f"{instrument}__volume_roc_{period}"] = df["volume"].pct_change(periods=period)
        
        # Standard deviation
        for period in kwargs.get('std_periods', [5, 13, 21, 55]):
            feature_dict[f"{instrument}__volume_std_{period}"] = df["volume"].rolling(window=period).std()
        
        # Volume max/min
        for period in kwargs.get('ma_periods', [5, 13, 21, 55]):
            feature_dict[f"{instrument}__volume_roll_max_{period}"] = df["volume"].rolling(window=period).max() / df["volume"]
            feature_dict[f"{instrument}__volume_roll_min_{period}"] = df["volume"].rolling(window=period).min() / df["volume"]
        
        # Bollinger Bands for volume
        for period in kwargs.get('bb_periods', [20]):
            mid = df["volume"].rolling(window=period).mean()
            std = df["volume"].rolling(window=period).std()
            feature_dict[f"{instrument}__volume_bb_mid_{period}"] = mid
            feature_dict[f"{instrument}__volume_bb_bbh_{period}"] = (df["volume"] - (mid + 2 * std)) / df["volume"]
            feature_dict[f"{instrument}__volume_bb_bbl_{period}"] = (df["volume"] - (mid - 2 * std)) / df["volume"]
        
        # On-Balance Volume
        obv = (df["volume"] * ((df["close"] > df["close"].shift(1)).astype(int) - 
                              (df["close"] < df["close"].shift(1)).astype(int))).cumsum()
        feature_dict[f"{instrument}__volume_obv"] = obv
        
        # OBV moving averages
        for period in kwargs.get('obv_periods', [3, 8, 21]):
            feature_dict[f"{instrument}__volume_obv_{period}"] = obv.rolling(window=period).mean()
    
    # Create DataFrame from all features at once to avoid fragmentation
    features = pd.DataFrame(feature_dict, index=df.index)
    
    # Clean up any infinite or NaN values
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.fillna(0)
    
    return features 