#!/usr/bin/env python
"""
Check USD_CHF features in the selected_features_per_instrument table.
"""

import pandas as pd
from trading_systems.rl.data.autoencoder_fusion import get_conn

def check_usd_chf_features():
    conn = get_conn()
    
    # Get USD_CHF features
    sql = """
    SELECT feature_name, rank 
    FROM selected_features_per_instrument 
    WHERE instrument = 'USD_CHF' 
    ORDER BY rank
    """
    
    df = pd.read_sql_query(sql, conn)
    
    print(f"Total selected features for USD_CHF: {len(df)}")
    print("\nSelected features for USD_CHF:")
    for i, row in df.iterrows():
        print(f"{row['rank']}. {row['feature_name']}")
    
    # Check for volume_roc_377 specifically
    volume_roc_377 = df[df['feature_name'] == 'volume_roc_377']
    if not volume_roc_377.empty:
        print("\nvolume_roc_377 is selected with rank:", volume_roc_377.iloc[0]['rank'])
    else:
        print("\nvolume_roc_377 is NOT in the selected features for USD_CHF")
    
    # Check what features with pattern 'volume' and pattern 'roc_377' are selected
    volume_features = df[df['feature_name'].str.contains('volume')]
    print(f"\nVolume-related features ({len(volume_features)}):")
    for i, row in volume_features.iterrows():
        print(f"{row['rank']}. {row['feature_name']}")
    
    roc_377_features = df[df['feature_name'].str.contains('roc_377')]
    print(f"\nROC_377 features ({len(roc_377_features)}):")
    for i, row in roc_377_features.iterrows():
        print(f"{row['rank']}. {row['feature_name']}")
    
    # Check feature name patterns in forex_features to see if prefixes are used
    sql_sample = "SELECT features FROM forex_features LIMIT 1"
    sample = pd.read_sql_query(sql_sample, conn)
    features_obj = sample.iloc[0, 0]
    
    print("\nSample of actual feature keys in forex_features:")
    for i, key in enumerate(list(features_obj.keys())[:10]):
        print(f"{i+1}. {key}")
    
    # Check if features in forex_features have instrument prefixes
    sql_features_count = "SELECT COUNT(*) FROM forex_features"
    count = pd.read_sql_query(sql_features_count, conn)
    print(f"\nTotal rows in forex_features: {count.iloc[0, 0]}")

if __name__ == "__main__":
    check_usd_chf_features() 