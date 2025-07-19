#!/usr/bin/env python
"""
Analyze USD_CHF volume data to identify why there are so many NaNs in the roc_377 feature.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from trading_systems.rl.data.autoencoder_fusion import get_conn

def analyze_volume_data():
    conn = get_conn()
    
    # Get all USD_CHF candle data
    sql = """
    SELECT timestamp, instrument, volume 
    FROM candles 
    WHERE instrument = 'USD_CHF' AND granularity = 'D' 
    ORDER BY timestamp ASC
    """
    
    df = pd.read_sql_query(sql, conn)
    
    print(f"Total USD_CHF records: {len(df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Check for zero or very small volumes
    zeros = (df['volume'] == 0).sum()
    ones = (df['volume'] == 1).sum()
    small = ((df['volume'] > 0) & (df['volume'] < 100)).sum()
    
    print(f"Zero volumes: {zeros} ({zeros/len(df)*100:.2f}%)")
    print(f"Volume = 1: {ones} ({ones/len(df)*100:.2f}%)")
    print(f"Small volumes (<100): {small} ({small/len(df)*100:.2f}%)")
    
    # Calculate the rate of change for volume with various lookback periods
    for period in [5, 21, 89, 377]:
        # Calculate ROC
        df[f'volume_roc_{period}'] = df['volume'].pct_change(periods=period)
        
        # Check for NaNs in ROC
        nans = df[f'volume_roc_{period}'].isna().sum()
        print(f"NaNs in volume_roc_{period}: {nans} ({nans/len(df)*100:.2f}%)")
        
        # Check for inf/extreme values
        inf_count = np.isinf(df[f'volume_roc_{period}']).sum()
        extreme = ((df[f'volume_roc_{period}'] > 100) | (df[f'volume_roc_{period}'] < -0.99)).sum()
        print(f"Inf values in volume_roc_{period}: {inf_count}")
        print(f"Extreme values in volume_roc_{period}: {extreme}")
        
        # For ROC_377, examine specific problem areas 
        if period == 377:
            # Look at the first 500 rows where we might expect NaNs
            initial_nans = df[f'volume_roc_{period}'].head(500).isna().sum()
            print(f"NaNs in first 500 rows of volume_roc_{period}: {initial_nans}")
            
            # Check where denominator (initial volume) is extremely small
            tiny_denominator = ((df['volume'].shift(period) < 10) & (~df[f'volume_roc_{period}'].isna())).sum()
            print(f"ROC_{period} calculations with tiny denominator (vol < 10): {tiny_denominator}")
            
            # Check for patterns in where NaNs occur
            nan_indices = df[df[f'volume_roc_{period}'].isna()].index
            if len(nan_indices) > 0:
                print(f"Sample of rows with NaN in volume_roc_{period}:")
                for idx in nan_indices[:5]:
                    if idx >= period:
                        current_vol = df.loc[idx, 'volume']
                        prev_vol = df.loc[idx-period, 'volume']
                        print(f"  Row {idx}: Current vol={current_vol}, Vol {period} days ago={prev_vol}")
    
    # Create histogram of volume values
    plt.figure(figsize=(10, 6))
    df['volume'].hist(bins=50)
    plt.title('Distribution of USD_CHF Volume')
    plt.yscale('log')
    plt.savefig('usd_chf_volume_histogram.png')
    
    # Plot volume over time to see if there are clear patterns
    plt.figure(figsize=(12, 6))
    df['volume'].plot()
    plt.title('USD_CHF Volume Over Time')
    plt.savefig('usd_chf_volume_time_series.png')
    
    # Look specifically at the earliest data
    early_data = df.head(500)
    plt.figure(figsize=(12, 6))
    early_data['volume'].plot()
    plt.title('Early USD_CHF Volume Data')
    plt.savefig('usd_chf_early_volume.png')

if __name__ == "__main__":
    analyze_volume_data() 