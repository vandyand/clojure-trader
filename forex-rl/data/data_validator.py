# data/data_validator.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from config.settings import config
from config.forex_pairs import FOREX_PAIRS, TOTAL_INPUT_FEATURES

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validates data quality and consistency for forex trading data
    Ensures data meets requirements for reliable ML training and inference
    """

    def __init__(self, 
                 max_missing_ratio: float = 0.1, 
                 outlier_threshold: float = 5.0,
                 min_data_points: int = 100):
        """
        Initialize data validator
        
        Args:
            max_missing_ratio: Maximum allowed ratio of missing values
            outlier_threshold: Z-score threshold for outlier detection
            min_data_points: Minimum required data points
        """
        self.max_missing_ratio = max_missing_ratio
        self.outlier_threshold = outlier_threshold
        self.min_data_points = min_data_points
        
        logger.info(f"Initialized DataValidator: max_missing={max_missing_ratio}, outlier_threshold={outlier_threshold}")

    def validate_price_data(self, df: pd.DataFrame, instrument: str) -> Tuple[bool, List[str]]:
        """
        Validate price data for a single instrument

        Args:
            df: Price DataFrame with OHLCV columns
            instrument: Instrument name for logging

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if df.empty:
            issues.append(f"{instrument}: DataFrame is empty")
            return False, issues

        # Check minimum data points
        if len(df) < self.min_data_points:
            issues.append(f"{instrument}: Only {len(df)} data points, minimum {self.min_data_points} required")

        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"{instrument}: Missing columns: {missing_columns}")
            return False, issues  # Can't continue without required columns

        # Check for missing values
        for col in required_columns:
            missing_count = df[col].isna().sum()
            missing_ratio = missing_count / len(df)
            if missing_ratio > self.max_missing_ratio:
                issues.append(f"{instrument}: {col} has {missing_ratio:.2%} missing values (max allowed: {self.max_missing_ratio:.2%})")

        # Check for negative or zero prices
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            non_positive_count = (df[col] <= 0).sum()
            if non_positive_count > 0:
                issues.append(f"{instrument}: {col} has {non_positive_count} non-positive values")

        # Check OHLC consistency
        if all(col in df.columns for col in price_columns):
            # High should be >= all other prices
            high_violations = (
                (df['high'] < df['open']) |
                (df['high'] < df['low']) |
                (df['high'] < df['close'])
            ).sum()
            if high_violations > 0:
                issues.append(f"{instrument}: {high_violations} high price violations (high < other prices)")

            # Low should be <= all other prices
            low_violations = (
                (df['low'] > df['open']) |
                (df['low'] > df['high']) |
                (df['low'] > df['close'])
            ).sum()
            if low_violations > 0:
                issues.append(f"{instrument}: {low_violations} low price violations (low > other prices)")

        # Check for outliers using z-score
        for col in price_columns:
            if df[col].std() > 0:  # Avoid division by zero
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_count = (z_scores > self.outlier_threshold).sum()
                if outlier_count > 0:
                    outlier_ratio = outlier_count / len(df)
                    if outlier_ratio > 0.05:  # More than 5% outliers
                        issues.append(f"{instrument}: {col} has {outlier_count} outliers ({outlier_ratio:.2%})")

        # Check for duplicate timestamps
        if df.index.duplicated().sum() > 0:
            issues.append(f"{instrument}: Found {df.index.duplicated().sum()} duplicate timestamps")

        # Check for gaps in time series (for daily data)
        if len(df) > 1:
            time_diffs = df.index.to_series().diff().dropna()
            expected_diff = pd.Timedelta(days=1)  # Assuming daily data
            
            # Allow for weekends (2-3 day gaps)
            large_gaps = time_diffs[time_diffs > pd.Timedelta(days=4)]
            if len(large_gaps) > 0:
                issues.append(f"{instrument}: Found {len(large_gaps)} large time gaps (>4 days)")

        # Check volume data
        if 'volume' in df.columns:
            zero_volume_count = (df['volume'] == 0).sum()
            if zero_volume_count > len(df) * 0.1:  # More than 10% zero volume
                issues.append(f"{instrument}: {zero_volume_count} periods with zero volume")

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_feature_data(self, features: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate feature data

        Args:
            features: Feature DataFrame

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

        # Check minimum data points
        if len(features) < self.min_data_points:
            issues.append(f"Only {len(features)} feature observations, minimum {self.min_data_points} required")

        # Check for infinite values
        inf_count = np.isinf(features.values).sum()
        if inf_count > 0:
            issues.append(f"Found {inf_count} infinite values")

        # Check for NaN values
        nan_count = features.isna().sum().sum()
        if nan_count > 0:
            nan_ratio = nan_count / (features.shape[0] * features.shape[1])
            if nan_ratio > self.max_missing_ratio:
                issues.append(f"Found {nan_count} NaN values ({nan_ratio:.2%})")

        # Check for constant features
        constant_features = []
        for col in features.columns:
            if features[col].std() == 0:
                constant_features.append(col)

        if constant_features:
            constant_ratio = len(constant_features) / features.shape[1]
            if constant_ratio > 0.1:  # More than 10% constant
                issues.append(f"Found {len(constant_features)} constant features ({constant_ratio:.2%})")

        # Check feature value ranges (log returns should be reasonable)
        extreme_features = []
        for col in features.columns:
            max_abs_value = features[col].abs().max()
            if max_abs_value > 10:  # Arbitrary threshold for log returns
                extreme_features.append((col, max_abs_value))

        if extreme_features:
            issues.append(f"Found {len(extreme_features)} features with extreme values (>10)")

        # Check for highly correlated features (might indicate data leakage)
        if features.shape[1] > 1:
            corr_matrix = features.corr().abs()
            # Set diagonal to 0 to ignore self-correlation
            np.fill_diagonal(corr_matrix.values, 0)
            
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if corr_matrix.iloc[i, j] > 0.95:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_matrix.iloc[i, j]))
            
            if high_corr_pairs:
                issues.append(f"Found {len(high_corr_pairs)} highly correlated feature pairs (>0.95)")

        is_valid = len(issues) == 0
        return is_valid, issues

    def clean_price_data(self, df: pd.DataFrame, instrument: str) -> pd.DataFrame:
        """
        Clean price data by fixing common issues

        Args:
            df: Price DataFrame
            instrument: Instrument name for logging

        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df

        cleaned = df.copy()
        original_length = len(cleaned)

        # Remove duplicate timestamps
        if cleaned.index.duplicated().sum() > 0:
            logger.info(f"{instrument}: Removing {cleaned.index.duplicated().sum()} duplicate timestamps")
            cleaned = cleaned[~cleaned.index.duplicated(keep='first')]

        # Sort by timestamp
        cleaned = cleaned.sort_index()

        # Fill missing values with forward fill, then backward fill
        missing_before = cleaned.isna().sum().sum()
        cleaned = cleaned.fillna(method='ffill').fillna(method='bfill')
        missing_after = cleaned.isna().sum().sum()
        
        if missing_before > missing_after:
            logger.info(f"{instrument}: Filled {missing_before - missing_after} missing values")

        # Fix non-positive prices
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in cleaned.columns:
                non_positive_mask = cleaned[col] <= 0
                non_positive_count = non_positive_mask.sum()
                
                if non_positive_count > 0:
                    logger.warning(f"{instrument}: Fixing {non_positive_count} non-positive {col} values")
                    # Replace with previous valid value
                    cleaned.loc[non_positive_mask, col] = np.nan
                    cleaned[col] = cleaned[col].fillna(method='ffill')
                    
                    # If still NaN (at beginning), use next valid value
                    cleaned[col] = cleaned[col].fillna(method='bfill')

        # Fix OHLC inconsistencies
        if all(col in cleaned.columns for col in price_columns):
            # Ensure high is the maximum of OHLC
            cleaned['high'] = cleaned[['open', 'high', 'low', 'close']].max(axis=1)
            # Ensure low is the minimum of OHLC
            cleaned['low'] = cleaned[['open', 'high', 'low', 'close']].min(axis=1)

        # Remove extreme outliers (beyond 5 standard deviations)
        for col in price_columns:
            if col in cleaned.columns and cleaned[col].std() > 0:
                mean_val = cleaned[col].mean()
                std_val = cleaned[col].std()
                lower_bound = mean_val - 5 * std_val
                upper_bound = mean_val + 5 * std_val
                
                outlier_mask = (cleaned[col] < lower_bound) | (cleaned[col] > upper_bound)
                outlier_count = outlier_mask.sum()
                
                if outlier_count > 0:
                    logger.warning(f"{instrument}: Clipping {outlier_count} extreme {col} outliers")
                    cleaned[col] = cleaned[col].clip(lower_bound, upper_bound)

        # Fix volume data
        if 'volume' in cleaned.columns:
            # Replace negative volume with 0
            negative_volume = (cleaned['volume'] < 0).sum()
            if negative_volume > 0:
                logger.warning(f"{instrument}: Fixing {negative_volume} negative volume values")
                cleaned.loc[cleaned['volume'] < 0, 'volume'] = 0

        logger.info(f"{instrument}: Cleaned data - {original_length} → {len(cleaned)} rows")
        return cleaned

    def validate_and_clean_all_data(self,
                                   price_data_dict: Dict[str, pd.DataFrame]
                                   ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, List[str]]]:
        """
        Validate and clean all price data

        Args:
            price_data_dict: Dictionary of price data

        Returns:
            Tuple of (cleaned_data_dict, validation_issues_dict)
        """
        cleaned_data = {}
        all_issues = {}
        
        logger.info(f"Validating and cleaning data for {len(price_data_dict)} instruments")

        for instrument, df in price_data_dict.items():
            # Validate original data
            is_valid, issues = self.validate_price_data(df, instrument)
            all_issues[instrument] = issues

            if not is_valid:
                logger.warning(f"Data quality issues for {instrument}: {len(issues)} issues found")
                for issue in issues[:5]:  # Log first 5 issues
                    logger.warning(f"  - {issue}")
                if len(issues) > 5:
                    logger.warning(f"  ... and {len(issues) - 5} more issues")

            # Clean data
            try:
                cleaned_df = self.clean_price_data(df, instrument)
                
                # Validate cleaned data
                is_valid_after, issues_after = self.validate_price_data(cleaned_df, instrument)
                
                if is_valid_after:
                    cleaned_data[instrument] = cleaned_df
                    logger.info(f"✓ {instrument}: Data cleaned and validated")
                else:
                    logger.error(f"✗ {instrument}: Still has issues after cleaning: {len(issues_after)} issues")
                    # Include anyway but log the issues
                    cleaned_data[instrument] = cleaned_df
                    all_issues[instrument].extend([f"After cleaning: {issue}" for issue in issues_after])
                    
            except Exception as e:
                logger.error(f"Error cleaning data for {instrument}: {e}")
                # Use original data if cleaning fails
                cleaned_data[instrument] = df

        logger.info(f"Data validation complete: {len(cleaned_data)} instruments processed")
        return cleaned_data, all_issues

    def get_data_quality_report(self, 
                               price_data_dict: Dict[str, pd.DataFrame],
                               feature_data: pd.DataFrame = None) -> Dict:
        """
        Generate comprehensive data quality report
        
        Args:
            price_data_dict: Dictionary of price data
            feature_data: Optional feature DataFrame
            
        Returns:
            Dictionary with data quality metrics
        """
        report = {
            'timestamp': pd.Timestamp.now(),
            'instruments': {},
            'summary': {},
            'features': {}
        }

        # Analyze each instrument
        total_issues = 0
        valid_instruments = 0
        
        for instrument, df in price_data_dict.items():
            is_valid, issues = self.validate_price_data(df, instrument)
            
            report['instruments'][instrument] = {
                'is_valid': is_valid,
                'issues': issues,
                'data_points': len(df),
                'date_range': {
                    'start': df.index.min() if not df.empty else None,
                    'end': df.index.max() if not df.empty else None
                },
                'missing_values': df.isna().sum().to_dict() if not df.empty else {},
                'price_ranges': {
                    col: {'min': df[col].min(), 'max': df[col].max()}
                    for col in ['open', 'high', 'low', 'close'] 
                    if col in df.columns and not df.empty
                }
            }
            
            total_issues += len(issues)
            if is_valid:
                valid_instruments += 1

        # Summary statistics
        report['summary'] = {
            'total_instruments': len(price_data_dict),
            'valid_instruments': valid_instruments,
            'invalid_instruments': len(price_data_dict) - valid_instruments,
            'total_issues': total_issues,
            'validation_success_rate': valid_instruments / len(price_data_dict) if price_data_dict else 0
        }

        # Feature analysis
        if feature_data is not None and not feature_data.empty:
            is_valid_features, feature_issues = self.validate_feature_data(feature_data)
            
            report['features'] = {
                'is_valid': is_valid_features,
                'issues': feature_issues,
                'shape': feature_data.shape,
                'missing_values': feature_data.isna().sum().sum(),
                'infinite_values': np.isinf(feature_data.values).sum(),
                'constant_features': (feature_data.std() == 0).sum(),
                'value_ranges': {
                    'min': feature_data.min().min(),
                    'max': feature_data.max().max(),
                    'mean_abs': feature_data.abs().mean().mean()
                }
            }

        return report

    def save_validation_report(self, report: Dict, filepath: str):
        """
        Save validation report to file
        
        Args:
            report: Validation report dictionary
            filepath: Path to save the report
        """
        try:
            import json
            
            # Convert non-serializable objects
            serializable_report = self._make_serializable(report)
            
            with open(filepath, 'w') as f:
                json.dump(serializable_report, f, indent=2, default=str)
                
            logger.info(f"Validation report saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving validation report: {e}")

    def _make_serializable(self, obj):
        """Convert non-serializable objects to serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif pd.isna(obj):
            return None
        else:
            return obj

# Convenience function for quick validation
def validate_forex_data(price_data_dict: Dict[str, pd.DataFrame], 
                       clean_data: bool = True) -> Tuple[Dict[str, pd.DataFrame], Dict]:
    """
    Convenience function to validate forex data
    
    Args:
        price_data_dict: Dictionary of price DataFrames
        clean_data: Whether to clean the data
        
    Returns:
        Tuple of (cleaned_data_dict, validation_report)
    """
    validator = DataValidator()
    
    if clean_data:
        cleaned_data, issues = validator.validate_and_clean_all_data(price_data_dict)
    else:
        cleaned_data = price_data_dict
        issues = {}
        for instrument, df in price_data_dict.items():
            _, instrument_issues = validator.validate_price_data(df, instrument)
            issues[instrument] = instrument_issues
    
    # Generate report
    report = validator.get_data_quality_report(cleaned_data)
    
    return cleaned_data, report 