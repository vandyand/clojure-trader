#!/usr/bin/env python
"""
Analyze forex_features table directly to identify why USD_CHF__volume_roc_377 has so many NaNs.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from trading_systems.rl.data.autoencoder_fusion import get_conn

def analyze_forex_features():
    conn = get_conn()
    
    # First, let's check how many rows have USD_CHF__volume_roc_377 as NULL
    sql_null_count = """
    SELECT COUNT(*) 
    FROM forex_features 
    WHERE features->>'USD_CHF__volume_roc_377' IS NULL
    """
    null_count = pd.read_sql_query(sql_null_count, conn)
    print(f"Total rows with NULL USD_CHF__volume_roc_377: {null_count.iloc[0, 0]}")
    
    # Get total rows for comparison
    sql_total = "SELECT COUNT(*) FROM forex_features"
    total_count = pd.read_sql_query(sql_total, conn)
    print(f"Total rows in forex_features: {total_count.iloc[0, 0]}")
    print(f"Percentage of NULLs: {null_count.iloc[0, 0] / total_count.iloc[0, 0] * 100:.2f}%")
    
    # Check if other long ROC features have similar issues
    roc_features = ['USD_CHF__volume_roc_377', 'EUR_USD__volume_roc_377', 'GBP_USD__volume_roc_377']
    
    for feature in roc_features:
        sql_feature_null = f"""
        SELECT COUNT(*) 
        FROM forex_features 
        WHERE features->>'%s' IS NULL
        """ % feature
        feature_null_count = pd.read_sql_query(sql_feature_null, conn)
        print(f"NULL count for {feature}: {feature_null_count.iloc[0, 0]} ({feature_null_count.iloc[0, 0] / total_count.iloc[0, 0] * 100:.2f}%)")
    
    # Get some sample rows with non-NULL values
    sql_samples = """
    SELECT timestamp, features->>'USD_CHF__volume_roc_377' as roc_377,
           features->>'USD_CHF__volume_roc_89' as roc_89,
           features->>'USD_CHF__volume' as volume
    FROM forex_features
    WHERE features->>'USD_CHF__volume_roc_377' IS NOT NULL
    ORDER BY timestamp
    LIMIT 10
    """
    samples = pd.read_sql_query(sql_samples, conn)
    print("\nSample rows with non-NULL USD_CHF__volume_roc_377:")
    print(samples)
    
    # Get the timestamp distribution where the feature is NULL
    sql_null_dates = """
    SELECT DATE_TRUNC('month', timestamp) as month, COUNT(*) as count
    FROM forex_features
    WHERE features->>'USD_CHF__volume_roc_377' IS NULL
    GROUP BY month
    ORDER BY month
    """
    null_dates = pd.read_sql_query(sql_null_dates, conn)
    print("\nDistribution of NULL values by month:")
    print(null_dates.head(10))  # Show first 10 months
    
    # Check if the NULLs are related to the date range
    sql_date_range = """
    SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
    FROM forex_features
    """
    date_range = pd.read_sql_query(sql_date_range, conn)
    print("\nDate range in forex_features:")
    print(date_range)
    
    # Calculate when we'd expect 377-day ROC to start having values
    earliest_date = pd.to_datetime(date_range.iloc[0, 0])
    roc_start_date = earliest_date + pd.Timedelta(days=377)
    print(f"Earliest date with 377 days of history available: {roc_start_date}")
    
    # Check for any patterns with other USD_CHF features
    sql_correlated = """
    SELECT timestamp, 
           features->>'USD_CHF__volume' as volume,
           features->>'USD_CHF__volume_roc_377' as roc_377,
           features->>'USD_CHF__volume_roc_89' as roc_89,
           features->>'USD_CHF__volume_roc_21' as roc_21
    FROM forex_features
    WHERE features->>'USD_CHF__volume' IS NOT NULL
    ORDER BY timestamp
    LIMIT 1000
    """
    correlated = pd.read_sql_query(sql_correlated, conn)
    
    # Convert to proper data types
    for col in ['volume', 'roc_377', 'roc_89', 'roc_21']:
        correlated[col] = pd.to_numeric(correlated[col], errors='coerce')
    
    # Count non-null values
    print("\nData quality of USD_CHF features in first 1000 rows:")
    print(f"Total rows: {len(correlated)}")
    print(f"Non-null volume: {correlated['volume'].notna().sum()} ({correlated['volume'].notna().sum()/len(correlated)*100:.2f}%)")
    print(f"Non-null roc_21: {correlated['roc_21'].notna().sum()} ({correlated['roc_21'].notna().sum()/len(correlated)*100:.2f}%)")
    print(f"Non-null roc_89: {correlated['roc_89'].notna().sum()} ({correlated['roc_89'].notna().sum()/len(correlated)*100:.2f}%)")
    print(f"Non-null roc_377: {correlated['roc_377'].notna().sum()} ({correlated['roc_377'].notna().sum()/len(correlated)*100:.2f}%)")
    
    # Check for missing periods where data should be available
    correlated['timestamp'] = pd.to_datetime(correlated['timestamp'])
    correlated = correlated.sort_values('timestamp')
    
    # Find gaps larger than 2 days
    correlated['date_diff'] = correlated['timestamp'].diff().dt.days
    large_gaps = correlated[correlated['date_diff'] > 2]
    
    if not large_gaps.empty:
        print("\nFound gaps in the data (> 2 days):")
        print(large_gaps[['timestamp', 'date_diff']].head(10))
    else:
        print("\nNo large gaps found in the timestamp sequence.")

if __name__ == "__main__":
    analyze_forex_features() 