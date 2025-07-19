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
    # Create a copy to avoid modifying the original
    features = pd.DataFrame(index=df.index)
    
    # Price-based features
    if kwargs.get('price_features', True):
        # Simple returns
        features[f"{instrument}__close_return"] = df["close"].pct_change()
        
        # Log returns
        features[f"{instrument}__close_log_return"] = np.log(df["close"] / df["close"].shift(1))
        
        # Price range
        features[f"{instrument}__high_low_range"] = (df["high"] - df["low"]) / df["close"]
        
        # Moving averages
        for period in kwargs.get('ma_periods', [3, 8, 21, 55, 144]):
            features[f"{instrument}__close_sma_{period}"] = df["close"].rolling(window=period).mean()
            features[f"{instrument}__close_ema_{period}"] = df["close"].ewm(span=period).mean()
        
        # Rate of change
        for period in kwargs.get('roc_periods', [1, 3, 8, 21, 55]):
            features[f"{instrument}__close_roc_{period}"] = df["close"].pct_change(periods=period)
        
        # Standard deviation
        for period in kwargs.get('std_periods', [5, 13, 21, 55]):
            features[f"{instrument}__close_std_{period}"] = df["close"].rolling(window=period).std()
        
        # Bollinger Bands
        for period in kwargs.get('bb_periods', [20]):
            mid = df["close"].rolling(window=period).mean()
            std = df["close"].rolling(window=period).std()
            features[f"{instrument}__close_bb_mid_{period}"] = mid
            features[f"{instrument}__close_bb_bbhi_{period}"] = (df["close"] - (mid + 2 * std)) / df["close"]
            features[f"{instrument}__close_bb_bblo_{period}"] = (df["close"] - (mid - 2 * std)) / df["close"]
        
        # RSI
        for period in kwargs.get('rsi_periods', [2, 8, 14]):
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss
            features[f"{instrument}__close_rsi_{period}"] = 100 - (100 / (1 + rs))
    
    # Volume-based features
    if 'volume' in df.columns and kwargs.get('volume_features', True):
        # Moving averages
        for period in kwargs.get('ma_periods', [3, 8, 21, 55, 144]):
            features[f"{instrument}__volume_sma_{period}"] = df["volume"].rolling(window=period).mean()
        
        # Rate of change
        for period in kwargs.get('roc_periods', [1, 3, 8, 21, 55]):
            features[f"{instrument}__volume_roc_{period}"] = df["volume"].pct_change(periods=period)
        
        # Standard deviation
        for period in kwargs.get('std_periods', [5, 13, 21, 55]):
            features[f"{instrument}__volume_std_{period}"] = df["volume"].rolling(window=period).std()
        
        # Volume max/min
        for period in kwargs.get('ma_periods', [5, 13, 21, 55]):
            features[f"{instrument}__volume_roll_max_{period}"] = df["volume"].rolling(window=period).max() / df["volume"]
            features[f"{instrument}__volume_roll_min_{period}"] = df["volume"].rolling(window=period).min() / df["volume"]
        
        # Bollinger Bands for volume
        for period in kwargs.get('bb_periods', [20]):
            mid = df["volume"].rolling(window=period).mean()
            std = df["volume"].rolling(window=period).std()
            features[f"{instrument}__volume_bb_mid_{period}"] = mid
            features[f"{instrument}__volume_bb_bbh_{period}"] = (df["volume"] - (mid + 2 * std)) / df["volume"]
            features[f"{instrument}__volume_bb_bbl_{period}"] = (df["volume"] - (mid - 2 * std)) / df["volume"]
        
        # On-Balance Volume
        obv = (df["volume"] * ((df["close"] > df["close"].shift(1)).astype(int) - 
                              (df["close"] < df["close"].shift(1)).astype(int))).cumsum()
        features[f"{instrument}__volume_obv"] = obv
        
        # OBV moving averages
        for period in kwargs.get('obv_periods', [3, 8, 21]):
            features[f"{instrument}__volume_obv_{period}"] = obv.rolling(window=period).mean()
    
    return features 