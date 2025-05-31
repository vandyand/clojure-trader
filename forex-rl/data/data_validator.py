import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

class DataValidator:
    """Data validation and cleaning for forex price data"""
    
    def __init__(self, max_missing_ratio: float = 0.1, outlier_threshold: float = 5.0):
        self.max_missing_ratio = max_missing_ratio
        self.outlier_threshold = outlier_threshold
    
    def validate_price_data(self, df: pd.DataFrame, instrument: str) -> Tuple[bool, List[str]]:
        """
        Validate price data for a single instrument
        
        Args:
            df: DataFrame with price data
            instrument: Instrument name
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        if df.empty:
            issues.append(f"{instrument}: DataFrame is empty")
            return False, issues
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"{instrument}: Missing columns: {missing_columns}")
        
        # Check for missing values
        for col in required_columns:
            if col in df.columns:
                missing_ratio = df[col].isna().sum() / len(df)
                if missing_ratio > self.max_missing_ratio:
                    issues.append(f"{instrument}: {col} has {missing_ratio:.2%} missing values")
        
        # Check for negative prices
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                negative_count = (df[col] <= 0).sum()
                if negative_count > 0:
                    issues.append(f"{instrument}: {col} has {negative_count} non-positive values")
        
        # Check OHLC consistency
        if all(col in df.columns for col in price_columns):
            # High should be >= Open, Low, Close
            high_violations = ((df['high'] < df['open']) | 
                              (df['high'] < df['low']) | 
                              (df['high'] < df['close'])).sum()
            if high_violations > 0:
                issues.append(f"{instrument}: {high_violations} high price violations")
            
            # Low should be <= Open, High, Close
            low_violations = ((df['low'] > df['open']) | 
                             (df['low'] > df['high']) | 
                             (df['low'] > df['close'])).sum()
            if low_violations > 0:
                issues.append(f"{instrument}: {low_violations} low price violations")
        
        # Check for outliers (using z-score)
        for col in price_columns:
            if col in df.columns:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_count = (z_scores > self.outlier_threshold).sum()
                if outlier_count > 0:
                    issues.append(f"{instrument}: {col} has {outlier_count} outliers")
        
        return len(issues) == 0, issues
    
    def clean_price_data(self, df: pd.DataFrame, instrument: str) -> pd.DataFrame:
        """
        Clean price data by fixing common issues
        
        Args:
            df: DataFrame with price data
            instrument: Instrument name
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        cleaned = df.copy()
        
        # Fill missing values with forward fill, then backward fill
        cleaned = cleaned.fillna(method='ffill').fillna(method='bfill')
        
        # Replace non-positive prices with previous valid values
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in cleaned.columns:
                # Replace non-positive values with NaN, then forward fill
                cleaned.loc[cleaned[col] <= 0, col] = np.nan
                cleaned[col] = cleaned[col].fillna(method='ffill')
        
        # Fix OHLC inconsistencies
        if all(col in cleaned.columns for col in price_columns):
            # Ensure high is the maximum of OHLC
            cleaned['high'] = cleaned[['open', 'high', 'low', 'close']].max(axis=1)
            # Ensure low is the minimum of OHLC
            cleaned['low'] = cleaned[['open', 'high', 'low', 'close']].min(axis=1)
        
        # Remove outliers by capping at 5 standard deviations
        for col in price_columns:
            if col in cleaned.columns:
                mean_val = cleaned[col].mean()
                std_val = cleaned[col].std()
                lower_bound = mean_val - 5 * std_val
                upper_bound = mean_val + 5 * std_val
                cleaned[col] = cleaned[col].clip(lower_bound, upper_bound)
        
        logger.info(f"Cleaned data for {instrument}: {len(cleaned)} rows")
        return cleaned
