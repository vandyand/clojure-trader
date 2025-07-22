"""
Feature Engineering for Unified Futures RL Trading System

This module combines:
1. Fibonacci sequence features for crypto pairs (300 features: 20 pairs × 15 periods)
2. Technical indicators for ETFs (782 features: 34 ETFs × 23 indicators)
3. Technical indicators for crypto pairs (160 features: 20 pairs × 8 indicators)

Total: 1,242 input features → 149-dimensional autoencoder bottleneck
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

# Try to import talib, with fallback to basic indicators
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available. Using basic technical indicators only.")

from constants import (
    CRYPTO_FUTURES_PAIRS, ETF_SYMBOLS, FIBONACCI_PERIODS,
    FIBONACCI_FEATURES, ETF_TOTAL_FEATURES, CRYPTO_TECHNICAL_FEATURES,
    TOTAL_INPUT_FEATURES
)

logger = logging.getLogger(__name__)

class FibonacciFeatureEngineer:
    """
    Calculates Fibonacci-based price ratios for crypto pairs.
    Formula: ln(price_t / price_{t-fib_period})
    """
    
    def __init__(self, periods: List[int] = None):
        self.periods = periods or FIBONACCI_PERIODS
        
    def calculate_fibonacci_features(self, prices: pd.Series) -> np.ndarray:
        """
        Calculate Fibonacci features for a single price series.
        
        Args:
            prices: Price series with datetime index
            
        Returns:
            Array of Fibonacci features [n_periods]
        """
        features = []
        
        for period in self.periods:
            if len(prices) > period:
                # Calculate log return over Fibonacci period
                current_price = prices.iloc[-1]
                past_price = prices.iloc[-1 - period]
                
                if past_price > 0:
                    feature = np.log(current_price / past_price)
                else:
                    feature = 0.0
            else:
                feature = 0.0
                
            features.append(feature)
            
        return np.array(features)
    
    def calculate_all_fibonacci_features(self, crypto_data: Dict[str, pd.DataFrame]) -> np.ndarray:
        """
        Calculate Fibonacci features for all crypto pairs.
        
        Args:
            crypto_data: Dictionary mapping pair symbols to OHLCV DataFrames
            
        Returns:
            Array of Fibonacci features [n_pairs * n_periods]
        """
        all_features = []
        
        for pair in CRYPTO_FUTURES_PAIRS:
            if pair in crypto_data:
                close_prices = crypto_data[pair]['close']
                pair_features = self.calculate_fibonacci_features(close_prices)
                all_features.extend(pair_features)
            else:
                # Fill with zeros if data missing
                all_features.extend([0.0] * len(self.periods))
                
        return np.array(all_features)

class TechnicalIndicatorEngineer:
    """
    Calculates technical indicators for ETFs and crypto pairs.
    """
    
    def __init__(self):
        self.etf_indicators = [
            'SMA_5', 'SMA_20', 'SMA_50', 'EMA_12', 'EMA_26',
            'RSI', 'MACD', 'MACD_SIGNAL', 'MACD_HIST',
            'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER', 'BB_WIDTH',
            'STOCH_K', 'STOCH_D', 'ATR', 'ADX',
            'CCI', 'WILLR', 'ROC', 'MOM', 'OBV', 'AD'
        ]
        
        self.crypto_indicators = [
            'RSI', 'MACD', 'BB_WIDTH', 'ATR', 'ADX', 'CCI', 'WILLR', 'ROC'
        ]
    
    def calculate_etf_indicators(self, df: pd.DataFrame) -> np.ndarray:
        """
        Calculate technical indicators for a single ETF.
        
        Args:
            df: OHLCV DataFrame with columns: open, high, low, close, volume
            
        Returns:
            Array of technical indicators [n_indicators]
        """
        indicators = []
        
        if TALIB_AVAILABLE:
            # Use TA-Lib for advanced indicators
            # Ensure data is float64 for talib compatibility
            close_prices = df['close'].values.astype(np.float64)
            high_prices = df['high'].values.astype(np.float64)
            low_prices = df['low'].values.astype(np.float64)
            volume_data = df['volume'].values.astype(np.float64)
            
            # Simple Moving Averages
            indicators.append(df['close'].rolling(5).mean().iloc[-1] if len(df) >= 5 else 0.0)
            indicators.append(df['close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else 0.0)
            indicators.append(df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else 0.0)
            
            # Exponential Moving Averages
            indicators.append(df['close'].ewm(span=12).mean().iloc[-1])
            indicators.append(df['close'].ewm(span=26).mean().iloc[-1])
            
            # RSI
            rsi = talib.RSI(close_prices)
            indicators.append(rsi[-1] if not np.isnan(rsi[-1]) else 50.0)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(close_prices)
            indicators.append(macd[-1] if not np.isnan(macd[-1]) else 0.0)
            indicators.append(macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0.0)
            indicators.append(macd_hist[-1] if not np.isnan(macd_hist[-1]) else 0.0)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices)
            indicators.append(bb_upper[-1] if not np.isnan(bb_upper[-1]) else df['close'].iloc[-1])
            indicators.append(bb_middle[-1] if not np.isnan(bb_middle[-1]) else df['close'].iloc[-1])
            indicators.append(bb_lower[-1] if not np.isnan(bb_lower[-1]) else df['close'].iloc[-1])
            
            # Bollinger Band Width
            bb_width = (bb_upper - bb_lower) / bb_middle
            indicators.append(bb_width[-1] if not np.isnan(bb_width[-1]) else 0.0)
            
            # Stochastic
            stoch_k, stoch_d = talib.STOCH(high_prices, low_prices, close_prices)
            indicators.append(stoch_k[-1] if not np.isnan(stoch_k[-1]) else 50.0)
            indicators.append(stoch_d[-1] if not np.isnan(stoch_d[-1]) else 50.0)
            
            # ATR
            atr = talib.ATR(high_prices, low_prices, close_prices)
            indicators.append(atr[-1] if not np.isnan(atr[-1]) else 0.0)
            
            # ADX
            adx = talib.ADX(high_prices, low_prices, close_prices)
            indicators.append(adx[-1] if not np.isnan(adx[-1]) else 25.0)
            
            # CCI
            cci = talib.CCI(high_prices, low_prices, close_prices)
            indicators.append(cci[-1] if not np.isnan(cci[-1]) else 0.0)
            
            # Williams %R
            willr = talib.WILLR(high_prices, low_prices, close_prices)
            indicators.append(willr[-1] if not np.isnan(willr[-1]) else -50.0)
            
            # Rate of Change
            roc = talib.ROC(close_prices)
            indicators.append(roc[-1] if not np.isnan(roc[-1]) else 0.0)
            
            # Momentum
            mom = talib.MOM(close_prices)
            indicators.append(mom[-1] if not np.isnan(mom[-1]) else 0.0)
            
            # On Balance Volume
            obv = talib.OBV(close_prices, volume_data)
            indicators.append(obv[-1] if not np.isnan(obv[-1]) else 0.0)
            
            # Accumulation/Distribution
            ad = talib.AD(high_prices, low_prices, close_prices, volume_data)
            indicators.append(ad[-1] if not np.isnan(ad[-1]) else 0.0)
            
        else:
            # Fallback to basic indicators using pandas
            # Simple Moving Averages
            indicators.append(df['close'].rolling(5).mean().iloc[-1] if len(df) >= 5 else 0.0)
            indicators.append(df['close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else 0.0)
            indicators.append(df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else 0.0)
            
            # Exponential Moving Averages
            indicators.append(df['close'].ewm(span=12).mean().iloc[-1])
            indicators.append(df['close'].ewm(span=26).mean().iloc[-1])
            
            # Basic RSI calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators.append(rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0)
            
            # Basic MACD
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            macd = ema12 - ema26
            macd_signal = macd.ewm(span=9).mean()
            macd_hist = macd - macd_signal
            indicators.append(macd.iloc[-1] if not np.isnan(macd.iloc[-1]) else 0.0)
            indicators.append(macd_signal.iloc[-1] if not np.isnan(macd_signal.iloc[-1]) else 0.0)
            indicators.append(macd_hist.iloc[-1] if not np.isnan(macd_hist.iloc[-1]) else 0.0)
            
            # Basic Bollinger Bands
            bb_middle = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            bb_width = (bb_upper - bb_lower) / bb_middle
            indicators.append(bb_upper.iloc[-1] if not np.isnan(bb_upper.iloc[-1]) else df['close'].iloc[-1])
            indicators.append(bb_middle.iloc[-1] if not np.isnan(bb_middle.iloc[-1]) else df['close'].iloc[-1])
            indicators.append(bb_lower.iloc[-1] if not np.isnan(bb_lower.iloc[-1]) else df['close'].iloc[-1])
            indicators.append(bb_width.iloc[-1] if not np.isnan(bb_width.iloc[-1]) else 0.0)
            
            # Basic Stochastic
            low_min = df['low'].rolling(14).min()
            high_max = df['high'].rolling(14).max()
            stoch_k = 100 * ((df['close'] - low_min) / (high_max - low_min))
            stoch_d = stoch_k.rolling(3).mean()
            indicators.append(stoch_k.iloc[-1] if not np.isnan(stoch_k.iloc[-1]) else 50.0)
            indicators.append(stoch_d.iloc[-1] if not np.isnan(stoch_d.iloc[-1]) else 50.0)
            
            # Basic ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean()
            indicators.append(atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else 0.0)
            
            # Basic ADX (simplified)
            indicators.append(25.0)  # Default neutral value
            
            # Basic CCI
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = typical_price.rolling(20).mean()
            mad = typical_price.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
            cci = (typical_price - sma_tp) / (0.015 * mad)
            indicators.append(cci.iloc[-1] if not np.isnan(cci.iloc[-1]) else 0.0)
            
            # Basic Williams %R
            highest_high = df['high'].rolling(14).max()
            lowest_low = df['low'].rolling(14).min()
            willr = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
            indicators.append(willr.iloc[-1] if not np.isnan(willr.iloc[-1]) else -50.0)
            
            # Rate of Change
            roc = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
            indicators.append(roc.iloc[-1] if not np.isnan(roc.iloc[-1]) else 0.0)
            
            # Momentum
            mom = df['close'] - df['close'].shift(10)
            indicators.append(mom.iloc[-1] if not np.isnan(mom.iloc[-1]) else 0.0)
            
            # Basic OBV
            obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
            indicators.append(obv.iloc[-1] if not np.isnan(obv.iloc[-1]) else 0.0)
            
            # Basic AD (simplified)
            indicators.append(0.0)  # Default value
        
        return np.array(indicators)
    
    def calculate_crypto_indicators(self, df: pd.DataFrame) -> np.ndarray:
        """
        Calculate technical indicators for a single crypto pair.
        
        Args:
            df: OHLCV DataFrame with columns: open, high, low, close, volume
            
        Returns:
            Array of technical indicators [n_indicators]
        """
        indicators = []
        
        if TALIB_AVAILABLE:
            # Use TA-Lib for advanced indicators
            # Ensure data is float64 for talib compatibility
            close_prices = df['close'].values.astype(np.float64)
            high_prices = df['high'].values.astype(np.float64)
            low_prices = df['low'].values.astype(np.float64)
            
            # RSI
            rsi = talib.RSI(close_prices)
            indicators.append(rsi[-1] if not np.isnan(rsi[-1]) else 50.0)
            
            # MACD
            macd, _, _ = talib.MACD(close_prices)
            indicators.append(macd[-1] if not np.isnan(macd[-1]) else 0.0)
            
            # Bollinger Band Width
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices)
            bb_width = (bb_upper - bb_lower) / bb_middle
            indicators.append(bb_width[-1] if not np.isnan(bb_width[-1]) else 0.0)
            
            # ATR
            atr = talib.ATR(high_prices, low_prices, close_prices)
            indicators.append(atr[-1] if not np.isnan(atr[-1]) else 0.0)
            
            # ADX
            adx = talib.ADX(high_prices, low_prices, close_prices)
            indicators.append(adx[-1] if not np.isnan(adx[-1]) else 25.0)
            
            # CCI
            cci = talib.CCI(high_prices, low_prices, close_prices)
            indicators.append(cci[-1] if not np.isnan(cci[-1]) else 0.0)
            
            # Williams %R
            willr = talib.WILLR(high_prices, low_prices, close_prices)
            indicators.append(willr[-1] if not np.isnan(willr[-1]) else -50.0)
            
            # Rate of Change
            roc = talib.ROC(close_prices)
            indicators.append(roc[-1] if not np.isnan(roc[-1]) else 0.0)
            
        else:
            # Fallback to basic indicators using pandas
            # Basic RSI calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators.append(rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0)
            
            # Basic MACD
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            macd = ema12 - ema26
            indicators.append(macd.iloc[-1] if not np.isnan(macd.iloc[-1]) else 0.0)
            
            # Basic Bollinger Band Width
            bb_middle = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            bb_width = (bb_upper - bb_lower) / bb_middle
            indicators.append(bb_width.iloc[-1] if not np.isnan(bb_width.iloc[-1]) else 0.0)
            
            # Basic ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean()
            indicators.append(atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else 0.0)
            
            # Basic ADX (simplified)
            indicators.append(25.0)  # Default neutral value
            
            # Basic CCI
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = typical_price.rolling(20).mean()
            mad = typical_price.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
            cci = (typical_price - sma_tp) / (0.015 * mad)
            indicators.append(cci.iloc[-1] if not np.isnan(cci.iloc[-1]) else 0.0)
            
            # Basic Williams %R
            highest_high = df['high'].rolling(14).max()
            lowest_low = df['low'].rolling(14).min()
            willr = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
            indicators.append(willr.iloc[-1] if not np.isnan(willr.iloc[-1]) else -50.0)
            
            # Rate of Change
            roc = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
            indicators.append(roc.iloc[-1] if not np.isnan(roc.iloc[-1]) else 0.0)
        
        return np.array(indicators)

class UnifiedFeatureEngineer:
    """
    Main feature engineering class that combines all feature types.
    """
    
    def __init__(self):
        self.fibonacci_engineer = FibonacciFeatureEngineer()
        self.technical_engineer = TechnicalIndicatorEngineer()
        self._feature_cache = {}  # Cache for computed features
        self._cache_hits = 0
        self._cache_misses = 0
        
    def engineer_features(self, 
                         crypto_data: Dict[str, pd.DataFrame],
                         etf_data: Dict[str, pd.DataFrame]) -> np.ndarray:
        """
        Engineer all features for the unified system.
        
        Args:
            crypto_data: Dictionary mapping crypto pair symbols to OHLCV DataFrames
            etf_data: Dictionary mapping ETF symbols to OHLCV DataFrames
            
        Returns:
            Combined feature array [TOTAL_INPUT_FEATURES]
        """
        # Create cache key based on data lengths (proxy for data state)
        cache_key = self._create_cache_key(crypto_data, etf_data)
        
        if cache_key in self._feature_cache:
            self._cache_hits += 1
            return self._feature_cache[cache_key]
        
        self._cache_misses += 1
        features = []
        
        # 1. Fibonacci features for crypto pairs (300 features)
        fib_features = self.fibonacci_engineer.calculate_all_fibonacci_features(crypto_data)
        features.extend(fib_features)
        
        # 2. Technical indicators for ETFs (782 features)
        for symbol in ETF_SYMBOLS:
            if symbol in etf_data:
                etf_indicators = self.technical_engineer.calculate_etf_indicators(etf_data[symbol])
                features.extend(etf_indicators)
            else:
                # Fill with zeros if data missing
                features.extend([0.0] * len(self.technical_engineer.etf_indicators))
        
        # 3. Technical indicators for crypto pairs (160 features)
        for pair in CRYPTO_FUTURES_PAIRS:
            if pair in crypto_data:
                crypto_indicators = self.technical_engineer.calculate_crypto_indicators(crypto_data[pair])
                features.extend(crypto_indicators)
            else:
                # Fill with zeros if data missing
                features.extend([0.0] * len(self.technical_engineer.crypto_indicators))
        
        feature_array = np.array(features)
        
        # Validate feature dimensions
        assert len(feature_array) == TOTAL_INPUT_FEATURES, \
            f"Expected {TOTAL_INPUT_FEATURES} features, got {len(feature_array)}"
        
        # Cache the result
        self._feature_cache[cache_key] = feature_array
        
        return feature_array
    
    def _create_cache_key(self, crypto_data: Dict[str, pd.DataFrame], 
                         etf_data: Dict[str, pd.DataFrame]) -> str:
        """Create a cache key based on data state."""
        crypto_lengths = tuple(len(df) for df in crypto_data.values())
        etf_lengths = tuple(len(df) for df in etf_data.values())
        return f"crypto_{crypto_lengths}_etf_{etf_lengths}"
    
    def clear_cache(self):
        """Clear the feature cache."""
        self._feature_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_size': len(self._feature_cache)
        }
    
    def get_feature_names(self) -> List[str]:
        """
        Get list of feature names for interpretability.
        
        Returns:
            List of feature names
        """
        feature_names = []
        
        # Fibonacci features
        for pair in CRYPTO_FUTURES_PAIRS:
            for period in FIBONACCI_PERIODS:
                feature_names.append(f"{pair}_FIB_{period}")
        
        # ETF technical indicators
        for symbol in ETF_SYMBOLS:
            for indicator in self.technical_engineer.etf_indicators:
                feature_names.append(f"{symbol}_{indicator}")
        
        # Crypto technical indicators
        for pair in CRYPTO_FUTURES_PAIRS:
            for indicator in self.technical_engineer.crypto_indicators:
                feature_names.append(f"{pair}_{indicator}")
        
        return feature_names
    
    def normalize_features(self, features: np.ndarray) -> np.ndarray:
        """
        Normalize features using robust scaling.
        
        Args:
            features: Raw feature array
            
        Returns:
            Normalized feature array
        """
        # Handle NaN and infinite values
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Robust scaling using median and IQR
        median = np.median(features)
        q75, q25 = np.percentile(features, [75, 25])
        iqr = q75 - q25
        
        if iqr == 0:
            return features - median
        else:
            return (features - median) / iqr 