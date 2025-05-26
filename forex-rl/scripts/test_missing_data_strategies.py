#!/usr/bin/env python3
"""
Test script for missing data handling strategies
Demonstrates different approaches to handling missing historical data in Fibonacci features
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from config.forex_pairs import FOREX_PAIRS, FIBONACCI_PERIODS
from data.oanda_client import OandaDataClient
from data.feature_engineer import FibonacciFeatureEngineer

def create_synthetic_data(n_days: int = 1000, start_price: float = 1.0) -> pd.DataFrame:
    """Create synthetic price data for testing"""
    dates = pd.date_range(start='2020-01-01', periods=n_days, freq='D')
    
    # Generate realistic price movements
    np.random.seed(42)
    returns = np.random.normal(0, 0.01, n_days)  # 1% daily volatility
    prices = start_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n_days)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.002, n_days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.002, n_days))),
        'close': prices,
        'volume': np.random.randint(10000, 100000, n_days)
    }, index=dates)
    
    return df

def test_missing_data_strategies():
    """Test different missing data strategies"""
    print("="*80)
    print("MISSING DATA STRATEGIES COMPARISON")
    print("="*80)
    
    # Create synthetic data
    print("Creating synthetic data...")
    price_data = create_synthetic_data(n_days=1000)
    print(f"Generated {len(price_data)} days of synthetic price data")
    print(f"Price range: {price_data['close'].min():.4f} - {price_data['close'].max():.4f}")
    
    # Test with single pair
    test_data = {"EUR_USD": price_data}
    
    strategies = ['forward_fill', 'zero', 'nan', 'skip_early']
    results = {}
    
    engineer = FibonacciFeatureEngineer()
    
    for strategy in strategies:
        print(f"\n{'-'*40}")
        print(f"Testing strategy: {strategy}")
        print(f"{'-'*40}")
        
        try:
            features = engineer.calculate_features_all_pairs(test_data, missing_data_strategy=strategy)
            
            if not features.empty:
                results[strategy] = features
                
                # Analyze the results
                print(f"Features shape: {features.shape}")
                print(f"NaN values: {features.isna().sum().sum()}")
                print(f"Zero values: (features == 0).sum().sum()")
                print(f"Infinite values: {np.isinf(features.values).sum()}")
                
                # Look at specific periods
                for period in [1, 233, 987]:
                    col_name = f"EUR_USD_fib_{period}"
                    if col_name in features.columns:
                        col_data = features[col_name]
                        print(f"  Period {period:3d}: first_10_values = {col_data.head(10).tolist()}")
                        print(f"  Period {period:3d}: nan_count = {col_data.isna().sum()}, zero_count = {(col_data == 0).sum()}")
                
            else:
                print("❌ No features generated")
                
        except Exception as e:
            print(f"❌ Error with strategy {strategy}: {e}")
    
    # Compare strategies visually
    if len(results) > 1:
        print(f"\n{'='*40}")
        print("STRATEGY COMPARISON")
        print(f"{'='*40}")
        
        # Compare first 1000 days for period 987 (most affected by missing data)
        comparison_data = {}
        for strategy, features in results.items():
            col_name = "EUR_USD_fib_987"
            if col_name in features.columns:
                comparison_data[strategy] = features[col_name].head(1000)
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            
            print("\nFirst 10 values for EUR_USD_fib_987:")
            print(comparison_df.head(10))
            
            print(f"\nStatistics for EUR_USD_fib_987 (first 1000 days):")
            print(comparison_df.describe())
            
            # Check how many valid (non-NaN, non-zero) values each strategy produces
            print(f"\nValid data availability:")
            for strategy in comparison_data.keys():
                data = comparison_data[strategy]
                valid_count = (~data.isna() & (data != 0)).sum()
                print(f"  {strategy:12s}: {valid_count:4d}/1000 valid values ({valid_count/10:.1f}%)")
    
    return results

def demonstrate_impact_on_training():
    """Demonstrate how different strategies affect training data"""
    print(f"\n{'='*80}")
    print("IMPACT ON TRAINING DATA")
    print(f"{'='*80}")
    
    # Create shorter dataset to emphasize the missing data problem
    short_data = create_synthetic_data(n_days=500)  # Only 500 days
    test_data = {"EUR_USD": short_data}
    
    engineer = FibonacciFeatureEngineer()
    
    strategies = ['forward_fill', 'zero']
    
    for strategy in strategies:
        print(f"\n{'-'*40}")
        print(f"Strategy: {strategy}")
        print(f"{'-'*40}")
        
        features = engineer.calculate_features_all_pairs(test_data, missing_data_strategy=strategy)
        
        if not features.empty:
            # Calculate how much data is actually usable for training
            usable_data = {}
            
            for period in FIBONACCI_PERIODS:
                col_name = f"EUR_USD_fib_{period}"
                if col_name in features.columns:
                    col_data = features[col_name]
                    
                    if strategy == 'forward_fill':
                        # All data is usable
                        usable_count = len(col_data)
                    elif strategy == 'zero':
                        # Only data after the lookback period is truly meaningful
                        usable_count = max(0, len(col_data) - period)
                    else:
                        # Count non-NaN values
                        usable_count = (~col_data.isna()).sum()
                    
                    usable_data[period] = usable_count
            
            print("Usable training samples by Fibonacci period:")
            for period, count in usable_data.items():
                percentage = (count / len(features)) * 100
                print(f"  Period {period:3d}: {count:3d}/{len(features)} samples ({percentage:5.1f}%)")
            
            # Overall impact
            if strategy == 'zero':
                # With zero strategy, we lose significant training data for long periods
                lost_samples = sum(period for period in FIBONACCI_PERIODS if period < len(features))
                total_possible = len(features) * len(FIBONACCI_PERIODS)
                loss_percentage = (lost_samples / total_possible) * 100
                print(f"\nOverall data loss with 'zero' strategy: {loss_percentage:.1f}%")

def recommend_best_practices():
    """Provide recommendations for best practices"""
    print(f"\n{'='*80}")
    print("INDUSTRY BEST PRACTICES & RECOMMENDATIONS")
    print(f"{'='*80}")
    
    recommendations = [
        {
            "strategy": "forward_fill",
            "pros": [
                "✅ No data loss - all observations can be used for training",
                "✅ Maintains temporal consistency",
                "✅ Provides meaningful baseline for price changes",
                "✅ Works well with normalization"
            ],
            "cons": [
                "⚠️ May introduce slight bias for very early observations",
                "⚠️ Assumes earliest price is representative"
            ],
            "use_case": "Recommended for most RL applications",
            "industry_usage": "Common in quantitative finance"
        },
        {
            "strategy": "zero",
            "pros": [
                "✅ Simple and interpretable",
                "✅ No assumptions about missing data"
            ],
            "cons": [
                "❌ Significant data loss (up to 987 days for longest period)",
                "❌ Creates artificial 'no change' signals",
                "❌ Reduces training data substantially"
            ],
            "use_case": "Only when you want to explicitly exclude uncertain data",
            "industry_usage": "Less common in production systems"
        },
        {
            "strategy": "skip_early",
            "pros": [
                "✅ Only uses data with full historical context",
                "✅ No assumptions about missing data",
                "✅ Highest data quality"
            ],
            "cons": [
                "❌ Significant data loss",
                "❌ May not have enough training data",
                "❌ Wastes early observations completely"
            ],
            "use_case": "Research or when data quality is paramount",
            "industry_usage": "Academic research, backtesting"
        }
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['strategy'].upper()} STRATEGY")
        print(f"   Use case: {rec['use_case']}")
        print(f"   Industry usage: {rec['industry_usage']}")
        print("   Pros:")
        for pro in rec['pros']:
            print(f"     {pro}")
        print("   Cons:")
        for con in rec['cons']:
            print(f"     {con}")
    
    print(f"\n{'='*40}")
    print("FINAL RECOMMENDATION")
    print(f"{'='*40}")
    print("🎯 Use 'forward_fill' strategy for production RL systems because:")
    print("   • Maximizes training data utilization")
    print("   • Provides meaningful price change baselines")
    print("   • Commonly used in quantitative finance")
    print("   • Works well with rolling normalization")
    print("   • Maintains temporal consistency")
    
    print(f"\n📊 Configuration update:")
    print("   Set missing_data_strategy = 'forward_fill' in config/settings.py")

def main():
    """Run all tests and demonstrations"""
    print("🔍 Testing Missing Data Handling Strategies for Fibonacci Features")
    print(f"📈 Using {len(FIBONACCI_PERIODS)} Fibonacci periods: {FIBONACCI_PERIODS}")
    
    # Test different strategies
    results = test_missing_data_strategies()
    
    # Demonstrate impact on training
    demonstrate_impact_on_training()
    
    # Provide recommendations
    recommend_best_practices()
    
    print(f"\n{'='*80}")
    print("✅ Missing data strategy analysis complete!")
    print("💡 Recommendation: Use 'forward_fill' strategy for optimal results")
    print(f"{'='*80}")

if __name__ == "__main__":
    main() 