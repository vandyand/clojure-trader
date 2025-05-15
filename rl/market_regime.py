import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from hmmlearn import hmm
import talib
import logging

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_regime")

class MarketRegimeDetector:
    """
    Detect market regimes across multiple instruments using various methods:
    1. Hidden Markov Models
    2. Gaussian Mixture Models
    3. Volatility-based regimes
    4. Trend strength indicators
    
    The detected regimes can be used to adapt trading strategies and position sizing.
    """
    
    REGIME_TYPES = {
        'STRONG_BULL': 5,
        'BULL': 4,
        'NEUTRAL': 3,
        'BEAR': 2,
        'STRONG_BEAR': 1,
        'VOLATILE': 0,
        'UNKNOWN': -1
    }
    
    def __init__(self, 
                window_size: int = 60,
                n_regimes: int = 3,
                volatility_lookback: int = 20,
                trend_lookback: int = 50):
        """
        Initialize the market regime detector
        
        Args:
            window_size: Window size for regime detection models
            n_regimes: Number of regimes to detect
            volatility_lookback: Lookback period for volatility calculation
            trend_lookback: Lookback period for trend strength calculation
        """
        self.window_size = window_size
        self.n_regimes = n_regimes
        self.volatility_lookback = volatility_lookback
        self.trend_lookback = trend_lookback
        
        # Models
        self.hmm_models = {}
        self.gmm_models = {}
        self.regime_history = {}
        
    def _prepare_features_for_model(self, prices: pd.DataFrame) -> np.ndarray:
        """
        Prepare regime detection features from price data
        
        Args:
            prices: DataFrame with price data (must have 'close' column)
            
        Returns:
            Feature array for regime detection models
        """
        # Extract close prices
        close_prices = prices['close'].values
        
        # Calculate returns
        returns = np.diff(np.log(close_prices))
        
        # Calculate features
        features = []
        
        # 1. Rolling volatility
        vol = np.array([np.std(returns[max(0, i-self.volatility_lookback):i+1]) 
                         for i in range(len(returns))])
        
        # 2. Rolling mean of returns
        mean_return = np.array([np.mean(returns[max(0, i-self.volatility_lookback):i+1]) 
                              for i in range(len(returns))])
        
        # 3. Return acceleration (change in returns)
        return_accel = np.diff(returns, prepend=0)
        
        # 4. Trend strength using log price vs SMA difference
        if len(close_prices) > self.trend_lookback:
            sma = np.array([np.mean(close_prices[max(0, i-self.trend_lookback):i+1]) 
                           for i in range(len(close_prices))])
            trend_strength = (close_prices - sma) / sma
        else:
            trend_strength = np.zeros_like(close_prices)
        
        # Combine features
        features = np.column_stack([
            returns,
            vol,
            mean_return,
            return_accel,
            trend_strength[1:]  # Align with returns length
        ])
        
        # Replace NaN and inf values
        features = np.nan_to_num(features, nan=0, posinf=0, neginf=0)
        
        return features
    
    def train_hmm_model(self, instrument: str, prices: pd.DataFrame) -> hmm.GaussianHMM:
        """
        Train a Hidden Markov Model for regime detection
        
        Args:
            instrument: Instrument name
            prices: DataFrame with price data
            
        Returns:
            Trained HMM model
        """
        # Prepare features
        features = self._prepare_features_for_model(prices)
        
        if len(features) < self.window_size:
            logger.warning(f"Not enough data for {instrument} to train HMM model")
            return None
        
        # Create and train HMM model
        model = hmm.GaussianHMM(n_components=self.n_regimes, 
                               covariance_type="full", 
                               n_iter=1000,
                               random_state=42)
        
        try:
            model.fit(features)
            self.hmm_models[instrument] = model
            logger.info(f"Trained HMM model for {instrument} with score {model.score(features):.2f}")
            return model
        except Exception as e:
            logger.error(f"Error training HMM model for {instrument}: {e}")
            return None
    
    def train_gmm_model(self, instrument: str, prices: pd.DataFrame) -> GaussianMixture:
        """
        Train a Gaussian Mixture Model for regime detection
        
        Args:
            instrument: Instrument name
            prices: DataFrame with price data
            
        Returns:
            Trained GMM model
        """
        # Prepare features
        features = self._prepare_features_for_model(prices)
        
        if len(features) < self.window_size:
            logger.warning(f"Not enough data for {instrument} to train GMM model")
            return None
        
        # Create and train GMM model
        model = GaussianMixture(n_components=self.n_regimes, 
                               covariance_type="full", 
                               random_state=42)
        
        try:
            model.fit(features)
            self.gmm_models[instrument] = model
            logger.info(f"Trained GMM model for {instrument}")
            return model
        except Exception as e:
            logger.error(f"Error training GMM model for {instrument}: {e}")
            return None
    
    def detect_volatility_regime(self, prices: pd.DataFrame) -> int:
        """
        Detect volatility regime based on recent volatility compared to historical
        
        Args:
            prices: DataFrame with price data
            
        Returns:
            Regime code (0-5)
        """
        if len(prices) < self.volatility_lookback * 2:
            return self.REGIME_TYPES['UNKNOWN']
        
        # Calculate returns
        returns = np.diff(np.log(prices['close'].values))
        
        # Current volatility (last lookback period)
        current_vol = np.std(returns[-self.volatility_lookback:])
        
        # Historical volatility (excluding current period)
        hist_returns = returns[:-self.volatility_lookback]
        if len(hist_returns) < self.volatility_lookback:
            return self.REGIME_TYPES['UNKNOWN']
            
        hist_vol = np.std(hist_returns)
        
        # Determine regime based on volatility ratio
        vol_ratio = current_vol / hist_vol if hist_vol > 0 else 1.0
        
        if vol_ratio > 2.0:
            return self.REGIME_TYPES['VOLATILE']
        elif vol_ratio < 0.5:
            return self.REGIME_TYPES['NEUTRAL']
        else:
            # If not extreme volatility, determine by trend
            mean_return = np.mean(returns[-self.volatility_lookback:])
            if mean_return > 0.0015:  # Strong positive trend
                return self.REGIME_TYPES['STRONG_BULL']
            elif mean_return > 0.0005:  # Moderate positive trend
                return self.REGIME_TYPES['BULL']
            elif mean_return < -0.0015:  # Strong negative trend
                return self.REGIME_TYPES['STRONG_BEAR']
            elif mean_return < -0.0005:  # Moderate negative trend
                return self.REGIME_TYPES['BEAR']
            else:
                return self.REGIME_TYPES['NEUTRAL']
    
    def detect_trend_regime(self, prices: pd.DataFrame) -> int:
        """
        Detect trend regime using multiple technical indicators
        
        Args:
            prices: DataFrame with price data
            
        Returns:
            Regime code (0-5)
        """
        if len(prices) < max(50, self.trend_lookback):
            return self.REGIME_TYPES['UNKNOWN']
        
        close_prices = prices['close'].values
        
        # Calculate various trend indicators
        # 1. ADX for trend strength
        if len(prices) >= 14 and 'high' in prices.columns and 'low' in prices.columns:
            adx = talib.ADX(prices['high'].values, prices['low'].values, close_prices, timeperiod=14)
            current_adx = adx[-1]
        else:
            current_adx = 0
        
        # 2. Price vs longer-term moving averages
        sma50 = talib.SMA(close_prices, timeperiod=min(50, len(close_prices)-1))
        sma200 = talib.SMA(close_prices, timeperiod=min(200, len(close_prices)-1))
        
        price_vs_sma50 = close_prices[-1] / sma50[-1] - 1 if sma50[-1] > 0 else 0
        price_vs_sma200 = close_prices[-1] / sma200[-1] - 1 if sma200[-1] > 0 else 0
        
        # 3. MACD
        macd, macd_signal, _ = talib.MACD(close_prices)
        macd_hist = macd[-1] - macd_signal[-1]
        
        # 4. RSI for overbought/oversold
        rsi = talib.RSI(close_prices)
        current_rsi = rsi[-1]
        
        # Determine trend regime
        trend_score = 0
        
        # ADX contribution (0-25 weak, 25-50 moderate, 50+ strong)
        if current_adx > 30:
            trend_score += 2
        elif current_adx > 20:
            trend_score += 1
        
        # Moving averages contribution
        if price_vs_sma50 > 0.03 and price_vs_sma200 > 0.05:
            trend_score += 2  # Strong uptrend
        elif price_vs_sma50 > 0.01 and price_vs_sma200 > 0:
            trend_score += 1  # Moderate uptrend
        elif price_vs_sma50 < -0.03 and price_vs_sma200 < -0.05:
            trend_score -= 2  # Strong downtrend
        elif price_vs_sma50 < -0.01 and price_vs_sma200 < 0:
            trend_score -= 1  # Moderate downtrend
        
        # MACD contribution
        if macd_hist > 0.01:
            trend_score += 1
        elif macd_hist < -0.01:
            trend_score -= 1
        
        # RSI contribution for extreme conditions
        if current_rsi > 70:
            trend_score = min(trend_score, 1)  # Cap uptrend in overbought
        elif current_rsi < 30:
            trend_score = max(trend_score, -1)  # Cap downtrend in oversold
        
        # Map score to regime
        if trend_score >= 3:
            return self.REGIME_TYPES['STRONG_BULL']
        elif trend_score == 2:
            return self.REGIME_TYPES['BULL']
        elif trend_score == -2:
            return self.REGIME_TYPES['BEAR']
        elif trend_score <= -3:
            return self.REGIME_TYPES['STRONG_BEAR']
        else:
            return self.REGIME_TYPES['NEUTRAL']
    
    def detect_hmm_regime(self, instrument: str, prices: pd.DataFrame) -> int:
        """
        Detect regime using HMM model
        
        Args:
            instrument: Instrument name
            prices: DataFrame with price data
            
        Returns:
            Regime code
        """
        # Train model if not available
        if instrument not in self.hmm_models:
            self.train_hmm_model(instrument, prices)
            
        if instrument not in self.hmm_models or self.hmm_models[instrument] is None:
            return self.REGIME_TYPES['UNKNOWN']
        
        # Prepare features
        features = self._prepare_features_for_model(prices)
        
        if len(features) < 5:  # Minimum data requirement
            return self.REGIME_TYPES['UNKNOWN']
        
        # Get regime prediction
        try:
            model = self.hmm_models[instrument]
            hidden_states = model.predict(features)
            current_state = hidden_states[-1]
            
            # Map HMM state to regime
            # We need to interpret these states based on the model
            # For simplicity, we'll analyze the mean return for each state
            state_returns = {}
            for state in range(self.n_regimes):
                state_mask = (hidden_states == state)
                if np.any(state_mask):
                    state_returns[state] = np.mean(features[state_mask, 0])  # Mean return
            
            # Sort states by mean return (ascending)
            sorted_states = sorted(state_returns.items(), key=lambda x: x[1])
            state_to_regime = {}
            
            # Map states to regimes based on mean returns
            if len(sorted_states) == 3:
                # 3-regime model:
                state_to_regime[sorted_states[0][0]] = self.REGIME_TYPES['BEAR']
                state_to_regime[sorted_states[1][0]] = self.REGIME_TYPES['NEUTRAL']
                state_to_regime[sorted_states[2][0]] = self.REGIME_TYPES['BULL']
            elif len(sorted_states) == 5:
                # 5-regime model
                state_to_regime[sorted_states[0][0]] = self.REGIME_TYPES['STRONG_BEAR']
                state_to_regime[sorted_states[1][0]] = self.REGIME_TYPES['BEAR']
                state_to_regime[sorted_states[2][0]] = self.REGIME_TYPES['NEUTRAL']
                state_to_regime[sorted_states[3][0]] = self.REGIME_TYPES['BULL']
                state_to_regime[sorted_states[4][0]] = self.REGIME_TYPES['STRONG_BULL']
            else:
                # Default mapping
                for i, (state, _) in enumerate(sorted_states):
                    if i == 0:
                        state_to_regime[state] = self.REGIME_TYPES['BEAR']
                    elif i == len(sorted_states) - 1:
                        state_to_regime[state] = self.REGIME_TYPES['BULL']
                    else:
                        state_to_regime[state] = self.REGIME_TYPES['NEUTRAL']
            
            return state_to_regime.get(current_state, self.REGIME_TYPES['NEUTRAL'])
            
        except Exception as e:
            logger.error(f"Error detecting HMM regime for {instrument}: {e}")
            return self.REGIME_TYPES['UNKNOWN']
    
    def detect_regime(self, instrument: str, prices: pd.DataFrame, method: str = 'ensemble') -> Dict[str, any]:
        """
        Detect market regime using specified method or ensemble
        
        Args:
            instrument: Instrument name
            prices: DataFrame with price data
            method: Detection method ('hmm', 'volatility', 'trend', or 'ensemble')
            
        Returns:
            Dictionary with regime information
        """
        regime_info = {
            'instrument': instrument,
            'timestamp': datetime.now(),
            'method': method,
            'regime_code': self.REGIME_TYPES['UNKNOWN'],
            'regime_name': 'UNKNOWN',
            'confidence': 0.0
        }
        
        if len(prices) < self.window_size:
            return regime_info
        
        if method == 'hmm':
            regime_code = self.detect_hmm_regime(instrument, prices)
            confidence = 0.7  # HMM confidence
        elif method == 'volatility':
            regime_code = self.detect_volatility_regime(prices)
            confidence = 0.6  # Volatility method confidence
        elif method == 'trend':
            regime_code = self.detect_trend_regime(prices)
            confidence = 0.65  # Trend method confidence
        elif method == 'ensemble':
            # Get predictions from all methods
            hmm_regime = self.detect_hmm_regime(instrument, prices)
            vol_regime = self.detect_volatility_regime(prices)
            trend_regime = self.detect_trend_regime(prices)
            
            # Count votes for each regime
            votes = {}
            if hmm_regime != self.REGIME_TYPES['UNKNOWN']:
                votes[hmm_regime] = votes.get(hmm_regime, 0) + 0.7  # Weighted vote
            if vol_regime != self.REGIME_TYPES['UNKNOWN']:
                votes[vol_regime] = votes.get(vol_regime, 0) + 0.6
            if trend_regime != self.REGIME_TYPES['UNKNOWN']:
                votes[trend_regime] = votes.get(trend_regime, 0) + 0.65
            
            # Select regime with most votes
            if votes:
                regime_code, vote_count = max(votes.items(), key=lambda x: x[1])
                confidence = vote_count / (0.7 + 0.6 + 0.65)  # Normalize
            else:
                regime_code = self.REGIME_TYPES['NEUTRAL']
                confidence = 0.5
        else:
            # Default to volatility method
            regime_code = self.detect_volatility_regime(prices)
            confidence = 0.6
        
        # Map regime code to name
        regime_name = next((name for name, code in self.REGIME_TYPES.items() 
                           if code == regime_code), 'UNKNOWN')
        
        # Update regime info
        regime_info['regime_code'] = regime_code
        regime_info['regime_name'] = regime_name
        regime_info['confidence'] = confidence
        
        # Add to regime history
        if instrument not in self.regime_history:
            self.regime_history[instrument] = []
        
        self.regime_history[instrument].append({
            'timestamp': datetime.now(),
            'regime_code': regime_code,
            'regime_name': regime_name,
            'method': method,
            'confidence': confidence
        })
        
        return regime_info

class AdaptivePositionSizer:
    """
    Adaptive position sizing that adjusts based on market regime
    and other risk factors.
    """
    
    def __init__(self, 
                 base_account_size: float = 1000.0,
                 base_risk_percent: float = 5.0,
                 max_risk_percent: float = 10.0,
                 min_risk_percent: float = 2.0,
                 volatility_adjustment: bool = True):
        """
        Initialize the adaptive position sizer
        
        Args:
            base_account_size: Base account size in USD
            base_risk_percent: Base risk percentage
            max_risk_percent: Maximum risk percentage
            min_risk_percent: Minimum risk percentage
            volatility_adjustment: Whether to adjust for volatility
        """
        self.base_account_size = base_account_size
        self.base_risk_percent = base_risk_percent
        self.max_risk_percent = max_risk_percent
        self.min_risk_percent = min_risk_percent
        self.volatility_adjustment = volatility_adjustment
        
        # Track current adjustments
        self.current_risk_percent = base_risk_percent
        self.regime_adjustments = {}
        
    def get_regime_adjustment(self, regime_info: Dict[str, any]) -> float:
        """
        Get position size adjustment factor based on market regime
        
        Args:
            regime_info: Regime information from MarketRegimeDetector
            
        Returns:
            Adjustment factor (multiplier for position size)
        """
        regime_code = regime_info['regime_code']
        confidence = regime_info['confidence']
        
        # Base adjustments by regime
        regime_adjustments = {
            # Regime Type: (factor, direction_bias)
            # Factor < 1 reduces position, > 1 increases it
            # Direction bias: positive means favor longs, negative means favor shorts
            5: (1.3, 0.5),    # STRONG_BULL: Increase size, favor longs
            4: (1.1, 0.3),    # BULL: Slight increase, slight favor for longs
            3: (1.0, 0.0),    # NEUTRAL: No adjustment
            2: (1.1, -0.3),   # BEAR: Slight increase, slight favor for shorts
            1: (1.3, -0.5),   # STRONG_BEAR: Increase size, favor shorts
            0: (0.7, 0.0),    # VOLATILE: Reduce size, no direction bias
            -1: (0.5, 0.0)    # UNKNOWN: Significantly reduce size
        }
        
        # Get adjustment for this regime
        factor, direction_bias = regime_adjustments.get(regime_code, (0.5, 0.0))
        
        # Scale by confidence
        factor = 1.0 + ((factor - 1.0) * confidence)
        direction_bias *= confidence
        
        # Store for future reference
        self.regime_adjustments[regime_info['instrument']] = {
            'factor': factor,
            'direction_bias': direction_bias,
            'regime': regime_info['regime_name']
        }
        
        return factor
    
    def adjust_position_sizes(self, 
                             positions: List[Dict[str, any]], 
                             regime_infos: Dict[str, Dict[str, any]],
                             volatilities: Dict[str, float] = None) -> List[Dict[str, any]]:
        """
        Adjust position sizes based on market regimes and volatility
        
        Args:
            positions: List of position dictionaries
            regime_infos: Dictionary mapping instruments to regime information
            volatilities: Dictionary mapping instruments to volatility (optional)
            
        Returns:
            Updated positions with adjusted sizes
        """
        adjusted_positions = []
        
        # Calculate overall risk adjustment based on regimes
        regime_factors = [self.get_regime_adjustment(info) 
                         for info in regime_infos.values() 
                         if info['regime_code'] != -1]  # Exclude unknown regimes
        
        if regime_factors:
            # Average adjustment factor across all instruments
            avg_regime_factor = sum(regime_factors) / len(regime_factors)
            
            # Adjust risk percent based on overall market conditions
            adjusted_risk_pct = self.base_risk_percent * avg_regime_factor
            
            # Clamp to limits
            adjusted_risk_pct = max(min(adjusted_risk_pct, self.max_risk_percent), self.min_risk_percent)
            
            # Update current risk percent
            self.current_risk_percent = adjusted_risk_pct
        else:
            # Default to base risk if no valid regimes
            self.current_risk_percent = self.base_risk_percent
        
        # Adjust each position
        for position in positions:
            instrument = position['instrument']
            adjusted_position = position.copy()
            
            # Apply regime-specific adjustments
            if instrument in regime_infos:
                regime_info = regime_infos[instrument]
                regime_factor = self.get_regime_adjustment(regime_info)
                
                # Get direction bias
                direction_bias = self.regime_adjustments[instrument]['direction_bias']
                
                # Adjust position size based on regime
                original_size = adjusted_position['position_size']
                original_direction = adjusted_position['direction']
                
                # Apply direction bias
                direction_factor = 1.0
                if original_direction == 'LONG' and direction_bias > 0:
                    direction_factor = 1.0 + direction_bias
                elif original_direction == 'SHORT' and direction_bias < 0:
                    direction_factor = 1.0 + abs(direction_bias)
                elif original_direction == 'LONG' and direction_bias < 0:
                    direction_factor = 1.0 - abs(direction_bias) * 0.5
                elif original_direction == 'SHORT' and direction_bias > 0:
                    direction_factor = 1.0 - direction_bias * 0.5
                
                # Apply volatility adjustment if enabled
                volatility_factor = 1.0
                if self.volatility_adjustment and volatilities and instrument in volatilities:
                    # Inverse relationship with volatility
                    vol = volatilities[instrument]
                    volatility_factor = 1.0 / (1.0 + vol)
                    # Ensure it stays in reasonable range
                    volatility_factor = max(min(volatility_factor, 1.5), 0.5)
                
                # Calculate final adjustment
                total_factor = regime_factor * direction_factor * volatility_factor
                
                # Update position size
                adjusted_position['position_size'] = original_size * total_factor
                
                # Update USD amount based on new position size
                price_ratio = adjusted_position['position_size'] / original_size if original_size != 0 else 1.0
                adjusted_position['usd_amount'] = adjusted_position['usd_amount'] * price_ratio
                
                # Add adjustment info
                adjusted_position['adjustment_factor'] = total_factor
                adjusted_position['regime'] = regime_info['regime_name']
            
            adjusted_positions.append(adjusted_position)
        
        return adjusted_positions

def calculate_volatilities(price_data: Dict[str, pd.DataFrame], window: int = 20) -> Dict[str, float]:
    """
    Calculate volatilities for all instruments
    
    Args:
        price_data: Dictionary mapping instruments to price DataFrames
        window: Window for volatility calculation
        
    Returns:
        Dictionary mapping instruments to annualized volatility
    """
    volatilities = {}
    
    for instrument, df in price_data.items():
        if len(df) < window + 1:
            continue
            
        # Calculate returns
        returns = np.diff(np.log(df['close'].values))
        
        if len(returns) < window:
            continue
            
        # Get recent volatility (annualized)
        recent_vol = np.std(returns[-window:]) * np.sqrt(252)
        volatilities[instrument] = recent_vol
    
    return volatilities

def main():
    """Example usage of market regime detection"""
    import json
    from api.oanda_api import get_candles
    
    # Setup
    regime_detector = MarketRegimeDetector(window_size=60, n_regimes=3)
    position_sizer = AdaptivePositionSizer(base_account_size=1000.0, base_risk_percent=5.0)
    
    # Sample instruments
    instruments = PAIRS_BY_LIQUIDITY_OANDA[:5]  # First 5 for example
    
    # Fetch historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=400)
    
    start_date_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    price_data = {}
    for instrument in instruments:
        try:
            candles = get_candles(instrument, "D", start_date_str, end_date_str)
            
            if not candles:
                logger.warning(f"No candles returned for {instrument}")
                continue
                
            # Parse candles into DataFrame
            data = []
            for candle in candles:
                timestamp = pd.to_datetime(candle["time"])
                
                # Extract OHLCV data
                ohlc = candle["mid"] if "mid" in candle else candle["bid"]
                row = {
                    "time": timestamp,
                    "open": float(ohlc["o"]),
                    "high": float(ohlc["h"]),
                    "low": float(ohlc["l"]),
                    "close": float(ohlc["c"]),
                    "volume": float(candle.get("volume", 0)),
                }
                data.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(data)
            df.set_index("time", inplace=True)
            df.sort_index(inplace=True)
            
            price_data[instrument] = df
            logger.info(f"Fetched {len(df)} candles for {instrument}")
            
        except Exception as e:
            logger.error(f"Error fetching data for {instrument}: {str(e)}")
    
    # Detect regimes for each instrument
    regime_infos = {}
    for instrument, df in price_data.items():
        regime_info = regime_detector.detect_regime(instrument, df, method='ensemble')
        regime_infos[instrument] = regime_info
        logger.info(f"{instrument} regime: {regime_info['regime_name']} (confidence: {regime_info['confidence']:.2f})")
    
    # Calculate volatilities
    volatilities = calculate_volatilities(price_data)
    
    # Create sample positions
    sample_positions = []
    for instrument in instruments:
        if instrument in price_data:
            direction = "LONG" if np.random.random() > 0.5 else "SHORT"
            position_size = np.random.random() * 0.5  # Random position size
            sample_positions.append({
                "instrument": instrument,
                "direction": direction,
                "position_size": position_size,
                "usd_amount": position_size * price_data[instrument]['close'].iloc[-1]
            })
    
    # Adjust positions based on regimes
    adjusted_positions = position_sizer.adjust_position_sizes(
        sample_positions, regime_infos, volatilities
    )
    
    # Print original vs adjusted positions
    logger.info("\nPosition Adjustments:")
    logger.info("Instrument | Direction | Original Size | Adjusted Size | Regime | Factor")
    logger.info("-" * 80)
    
    for i, pos in enumerate(adjusted_positions):
        orig = sample_positions[i]
        logger.info(f"{pos['instrument']} | {pos['direction']} | {orig['position_size']:.4f} | {pos['position_size']:.4f} | {pos['regime']} | {pos['adjustment_factor']:.2f}")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "regimes": {k: v for k, v in regime_infos.items()},
        "volatilities": {k: float(v) for k, v in volatilities.items()},
        "adjusted_positions": adjusted_positions
    }
    
    with open(f"market_regime_analysis_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
        # Convert non-serializable objects to strings
        import json
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        
        json.dump(results, f, indent=2, cls=DateTimeEncoder)
    
    logger.info(f"Results saved to market_regime_analysis_{datetime.now().strftime('%Y%m%d')}.json")

if __name__ == "__main__":
    main() 