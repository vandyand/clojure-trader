# data/feature_engineer.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from config.settings import config
from config.forex_pairs import FOREX_PAIRS, FIBONACCI_PERIODS, TOTAL_INPUT_FEATURES

logger = logging.getLogger(__name__)

class FibonacciFeatureEngineer:
    """
    Calculates Fibonacci-based price features for forex pairs
    Feature formula: ln(price_t / price_{t-fib_period})
    
    With 15 Fibonacci periods and 20 forex pairs, generates 300 features total.
    """

    def __init__(self, fibonacci_periods: List[int] = None):
        """
        Initialize feature engineer
        
        Args:
            fibonacci_periods: List of Fibonacci periods (defaults to config)
        """
        self.fibonacci_periods = fibonacci_periods or FIBONACCI_PERIODS
        self.n_periods = len(self.fibonacci_periods)
        self.n_pairs = len(FOREX_PAIRS)
        self.total_features = self.n_pairs * self.n_periods
        
        logger.info(f"Initialized FibonacciFeatureEngineer: {self.n_pairs} pairs × {self.n_periods} periods = {self.total_features} features")
        
        # Validate configuration
        assert self.total_features == TOTAL_INPUT_FEATURES, f"Feature count mismatch: {self.total_features} != {TOTAL_INPUT_FEATURES}"

    def calculate_features_single_pair(self, price_data: pd.DataFrame, pair_name: str, 
                                      missing_data_strategy: str = 'forward_fill') -> pd.DataFrame:
        """
        Calculate Fibonacci features for a single forex pair

        Args:
            price_data: DataFrame with OHLCV data
            pair_name: Name of the forex pair
            missing_data_strategy: Strategy for handling missing historical data
                - 'forward_fill': Use earliest available price for missing lookbacks
                - 'zero': Set to 0.0 (no change) - current behavior
                - 'nan': Leave as NaN (will be handled downstream)
                - 'skip_early': Only calculate features where full history exists

        Returns:
            DataFrame with calculated features (15 columns)
        """
        if price_data.empty or 'close' not in price_data.columns:
            logger.warning(f"Invalid price data for {pair_name}")
            return pd.DataFrame()

        features = pd.DataFrame(index=price_data.index)
        close_prices = price_data['close']

        for period in self.fibonacci_periods:
            feature_name = f"{pair_name}_fib_{period}"

            if len(close_prices) > period:
                # Standard case: sufficient historical data
                shifted_prices = close_prices.shift(period)
                
                # Avoid division by zero and log of negative numbers
                valid_mask = (shifted_prices > 0) & (close_prices > 0)
                feature_values = pd.Series(np.nan, index=close_prices.index)
                
                feature_values[valid_mask] = np.log(close_prices[valid_mask] / shifted_prices[valid_mask])
                
                # Handle the missing historical data at the beginning
                if missing_data_strategy == 'forward_fill':
                    # Use the earliest available price for missing lookbacks
                    earliest_price = close_prices.iloc[0]
                    if earliest_price > 0:
                        # For the first 'period' observations, use earliest price as reference
                        for i in range(min(period, len(close_prices))):
                            if close_prices.iloc[i] > 0:
                                feature_values.iloc[i] = np.log(close_prices.iloc[i] / earliest_price)
                
                elif missing_data_strategy == 'zero':
                    # Set missing values to 0 (no change)
                    feature_values = feature_values.fillna(0.0)
                
                elif missing_data_strategy == 'nan':
                    # Leave as NaN - will be handled by normalization or downstream
                    pass
                
                elif missing_data_strategy == 'skip_early':
                    # Only provide values where full lookback exists
                    # First 'period' values remain NaN
                    pass
                
                # Handle infinite and remaining NaN values
                feature_values = feature_values.replace([np.inf, -np.inf], np.nan)
                
                # Final cleanup based on strategy
                if missing_data_strategy in ['forward_fill', 'zero']:
                    feature_values = feature_values.fillna(0.0)

                features[feature_name] = feature_values
                
            else:
                # Insufficient data for this period across entire dataset
                logger.debug(f"Not enough data for {pair_name} period {period} (need {period}, have {len(close_prices)})")
                
                if missing_data_strategy == 'forward_fill':
                    # Use earliest available price for all observations
                    if len(close_prices) > 0:
                        earliest_price = close_prices.iloc[0]
                        if earliest_price > 0:
                            feature_values = np.log(close_prices / earliest_price)
                            feature_values = feature_values.replace([np.inf, -np.inf], 0.0)
                            feature_values = feature_values.fillna(0.0)
                            features[feature_name] = feature_values
                        else:
                            features[feature_name] = 0.0
                    else:
                        features[feature_name] = 0.0
                elif missing_data_strategy == 'zero':
                    features[feature_name] = 0.0
                elif missing_data_strategy == 'nan':
                    features[feature_name] = np.nan
                elif missing_data_strategy == 'skip_early':
                    features[feature_name] = np.nan

        return features

    def calculate_features_all_pairs(self, price_data_dict: Dict[str, pd.DataFrame], 
                                    missing_data_strategy: str = 'forward_fill') -> pd.DataFrame:
        """
        Calculate Fibonacci features for all forex pairs

        Args:
            price_data_dict: Dictionary mapping pair names to price DataFrames
            missing_data_strategy: Strategy for handling missing historical data

        Returns:
            DataFrame with all features (300 columns)
        """
        if not price_data_dict:
            logger.error("No price data provided")
            return pd.DataFrame()

        all_features = []
        feature_names = []

        # Get common time index across all instruments
        common_index = None
        valid_pairs = []
        
        for pair in FOREX_PAIRS:
            if pair in price_data_dict and not price_data_dict[pair].empty:
                df = price_data_dict[pair]
                if common_index is None:
                    common_index = df.index
                else:
                    common_index = common_index.intersection(df.index)
                valid_pairs.append(pair)

        if common_index is None or len(common_index) == 0:
            logger.error("No common time index found across instruments")
            return pd.DataFrame()

        logger.info(f"Common time index: {len(common_index)} timestamps, {len(valid_pairs)} valid pairs")

        # Calculate features for each pair
        for pair in FOREX_PAIRS:
            if pair in price_data_dict and not price_data_dict[pair].empty:
                # Calculate features for this pair
                pair_features = self.calculate_features_single_pair(
                    price_data_dict[pair], pair, missing_data_strategy
                )

                if not pair_features.empty:
                    # Reindex to common index
                    pair_features = pair_features.reindex(common_index, fill_value=0.0)
                    all_features.append(pair_features)
                    logger.debug(f"✓ {pair}: {pair_features.shape[1]} features calculated")
                else:
                    # Create zero features for failed calculation
                    logger.warning(f"Failed to calculate features for {pair}, using zeros")
                    zero_features = pd.DataFrame(
                        0.0,
                        index=common_index,
                        columns=[f"{pair}_fib_{period}" for period in self.fibonacci_periods]
                    )
                    all_features.append(zero_features)
            else:
                logger.warning(f"No data for {pair}, filling with zeros")
                # Create zero features for missing pair
                zero_features = pd.DataFrame(
                    0.0,
                    index=common_index,
                    columns=[f"{pair}_fib_{period}" for period in self.fibonacci_periods]
                )
                all_features.append(zero_features)

            # Track feature names for this pair
            for period in self.fibonacci_periods:
                feature_names.append(f"{pair}_fib_{period}")

        # Combine all features
        if all_features:
            combined_features = pd.concat(all_features, axis=1)
            combined_features.columns = feature_names

            # Final validation and cleanup
            combined_features = combined_features.fillna(0.0)
            combined_features = combined_features.replace([np.inf, -np.inf], 0.0)

            logger.info(f"Generated features shape: {combined_features.shape}")
            
            # Validate expected shape
            expected_shape = (len(common_index), TOTAL_INPUT_FEATURES)
            if combined_features.shape != expected_shape:
                logger.error(f"Feature shape mismatch: got {combined_features.shape}, expected {expected_shape}")
            
            return combined_features
        else:
            logger.error("No features could be calculated")
            return pd.DataFrame()

    def normalize_features(self, features: pd.DataFrame, 
                          window: int = None, 
                          method: str = 'zscore') -> pd.DataFrame:
        """
        Apply normalization to features

        Args:
            features: Feature DataFrame
            window: Rolling window size (defaults to config value)
            method: Normalization method ('zscore', 'minmax', 'robust')

        Returns:
            Normalized features
        """
        if features.empty:
            return features

        window = window or config.data.normalization_window
        normalized = features.copy()

        if method == 'zscore':
            # Rolling z-score normalization
            for column in features.columns:
                rolling_mean = features[column].rolling(window=window, min_periods=1).mean()
                rolling_std = features[column].rolling(window=window, min_periods=1).std()

                # Avoid division by zero
                rolling_std = rolling_std.replace(0, 1e-8)

                normalized[column] = (features[column] - rolling_mean) / rolling_std

        elif method == 'minmax':
            # Rolling min-max normalization
            for column in features.columns:
                rolling_min = features[column].rolling(window=window, min_periods=1).min()
                rolling_max = features[column].rolling(window=window, min_periods=1).max()
                
                # Avoid division by zero
                rolling_range = rolling_max - rolling_min
                rolling_range = rolling_range.replace(0, 1e-8)
                
                normalized[column] = (features[column] - rolling_min) / rolling_range

        elif method == 'robust':
            # Rolling robust normalization (median and MAD)
            for column in features.columns:
                rolling_median = features[column].rolling(window=window, min_periods=1).median()
                rolling_mad = features[column].rolling(window=window, min_periods=1).apply(
                    lambda x: np.median(np.abs(x - np.median(x)))
                )
                
                # Avoid division by zero
                rolling_mad = rolling_mad.replace(0, 1e-8)
                
                normalized[column] = (features[column] - rolling_median) / rolling_mad

        else:
            raise ValueError(f"Unknown normalization method: {method}")

        # Final cleanup
        normalized = normalized.fillna(0.0)
        normalized = normalized.replace([np.inf, -np.inf], 0.0)

        logger.info(f"Applied {method} normalization with window={window}")
        return normalized

    def get_latest_features(self, price_data_dict: Dict[str, pd.DataFrame], 
                           normalize: bool = True,
                           missing_data_strategy: str = 'forward_fill') -> np.ndarray:
        """
        Get the latest feature vector for real-time inference

        Args:
            price_data_dict: Dictionary of price data
            normalize: Whether to apply normalization
            missing_data_strategy: Strategy for handling missing historical data

        Returns:
            Latest feature vector (300 dimensions)
        """
        features_df = self.calculate_features_all_pairs(price_data_dict, missing_data_strategy)

        if features_df.empty:
            logger.warning("No features calculated, returning zero vector")
            return np.zeros(TOTAL_INPUT_FEATURES, dtype=np.float32)

        # Apply normalization if requested
        if normalize:
            features_df = self.normalize_features(features_df)

        # Return latest row
        latest_features = features_df.iloc[-1].values

        # Ensure correct shape
        if len(latest_features) != TOTAL_INPUT_FEATURES:
            logger.warning(f"Feature vector has {len(latest_features)} dimensions, expected {TOTAL_INPUT_FEATURES}")
            # Pad or truncate to expected size
            if len(latest_features) < TOTAL_INPUT_FEATURES:
                latest_features = np.pad(latest_features, (0, TOTAL_INPUT_FEATURES - len(latest_features)))
            else:
                latest_features = latest_features[:TOTAL_INPUT_FEATURES]

        return latest_features.astype(np.float32)

    def get_feature_names(self) -> List[str]:
        """
        Get list of all feature names
        
        Returns:
            List of feature names
        """
        feature_names = []
        for pair in FOREX_PAIRS:
            for period in self.fibonacci_periods:
                feature_names.append(f"{pair}_fib_{period}")
        return feature_names

    def validate_features(self, features: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate feature DataFrame
        
        Args:
            features: Feature DataFrame to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if features.empty:
            issues.append("Feature DataFrame is empty")
            return False, issues

        # Check expected shape
        if features.shape[1] != TOTAL_INPUT_FEATURES:
            issues.append(f"Expected {TOTAL_INPUT_FEATURES} features, got {features.shape[1]}")

        # Check for infinite values
        inf_count = np.isinf(features.values).sum()
        if inf_count > 0:
            issues.append(f"Found {inf_count} infinite values")

        # Check for NaN values
        nan_count = features.isna().sum().sum()
        if nan_count > 0:
            issues.append(f"Found {nan_count} NaN values")

        # Check for constant features (might indicate data issues)
        constant_features = []
        for col in features.columns:
            if features[col].std() == 0:
                constant_features.append(col)

        if len(constant_features) > len(features.columns) * 0.1:  # More than 10% constant
            issues.append(f"Found {len(constant_features)} constant features (may indicate data issues)")

        # Check feature value ranges (should be reasonable after log transformation)
        extreme_features = []
        for col in features.columns:
            if features[col].abs().max() > 10:  # Arbitrary threshold for log returns
                extreme_features.append(col)

        if extreme_features:
            issues.append(f"Found {len(extreme_features)} features with extreme values (>10)")

        is_valid = len(issues) == 0
        return is_valid, issues

    def get_feature_statistics(self, features: pd.DataFrame) -> Dict:
        """
        Get comprehensive statistics about features
        
        Args:
            features: Feature DataFrame
            
        Returns:
            Dictionary with feature statistics
        """
        if features.empty:
            return {}

        stats = {
            'shape': features.shape,
            'total_features': features.shape[1],
            'total_observations': features.shape[0],
            'missing_values': features.isna().sum().sum(),
            'infinite_values': np.isinf(features.values).sum(),
            'mean_abs_value': features.abs().mean().mean(),
            'std_across_features': features.std().mean(),
            'min_value': features.min().min(),
            'max_value': features.max().max(),
            'constant_features': (features.std() == 0).sum(),
            'feature_names': list(features.columns)
        }

        return stats

# Convenience function for quick feature calculation
def calculate_forex_features(price_data_dict: Dict[str, pd.DataFrame], 
                           normalize: bool = True,
                           normalization_method: str = 'zscore',
                           missing_data_strategy: str = 'forward_fill') -> pd.DataFrame:
    """
    Convenience function to calculate forex features
    
    Args:
        price_data_dict: Dictionary of price DataFrames
        normalize: Whether to apply normalization
        normalization_method: Method for normalization
        missing_data_strategy: Strategy for handling missing historical data
        
    Returns:
        Feature DataFrame
    """
    engineer = FibonacciFeatureEngineer()
    features = engineer.calculate_features_all_pairs(price_data_dict, missing_data_strategy)
    
    if normalize and not features.empty:
        features = engineer.normalize_features(features, method=normalization_method)
    
    return features 