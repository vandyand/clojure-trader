#!/usr/bin/env python
"""
Check what feature names actually exist in the forex_features table.
"""

import pandas as pd
import json
from trading_systems.rl.data.autoencoder_fusion import get_conn

def check_feature_names():
    conn = get_conn()
    
    # Get a sample row
    sql = "SELECT features FROM forex_features LIMIT 1"
    sample = pd.read_sql_query(sql, conn)
    
    # Examine the features object
    features_obj = sample.iloc[0, 0]
    print(f"Features column type: {type(features_obj)}")
    print(f"Features column first 5 keys: {list(features_obj.keys())[:5]}")
    
    # Print the number of keys
    feature_keys = list(features_obj.keys())
    feature_keys.sort()
    print(f"Total features: {len(feature_keys)}")
    
    # Print first few keys for reference
    print("\nSample feature names:")
    for i, key in enumerate(feature_keys[:10]):
        print(f"{i+1}. {key}")
    
    # Check for specific pattern matches
    pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF']
    for pair in pairs:
        pair_features = [f for f in feature_keys if pair in f]
        print(f"\n{pair} features: {len(pair_features)}")
        if pair_features:
            for i, feature in enumerate(pair_features[:5]):
                print(f"{i+1}. {feature}")
    
    # Check for ROC features of different timeframes
    timeframes = [5, 21, 89, 377]
    for tf in timeframes:
        roc_features = [f for f in feature_keys if f'roc_{tf}' in f]
        print(f"\nroc_{tf} features: {len(roc_features)}")
        if roc_features:
            for i, feature in enumerate(roc_features[:5]):
                print(f"{i+1}. {feature}")
    
    # Check the selected_features_per_instrument table structure
    sql_selected_cols = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'selected_features_per_instrument'
    """
    selected_cols = pd.read_sql_query(sql_selected_cols, conn)
    print("\nColumns in selected_features_per_instrument table:")
    print(selected_cols)
    
    # Get the content from selected_features_per_instrument
    sql_selected = "SELECT * FROM selected_features_per_instrument LIMIT 5"
    selected = pd.read_sql_query(sql_selected, conn)
    print("\nSample rows from selected_features_per_instrument:")
    print(selected)
    
    # Check if USD_CHF is in the selected_features_per_instrument table
    sql_usd_chf = "SELECT * FROM selected_features_per_instrument WHERE instrument = 'USD_CHF'"
    usd_chf_selected = pd.read_sql_query(sql_usd_chf, conn)
    if not usd_chf_selected.empty:
        print("\nUSD_CHF entry found in selected_features_per_instrument")
        # Get the feature names if available
        if 'feature_names' in usd_chf_selected.columns:
            try:
                features_list = json.loads(usd_chf_selected.iloc[0]['feature_names'])
                print(f"Feature count: {len(features_list)}")
                print("First 10 features:")
                for i, feature in enumerate(features_list[:10]):
                    print(f"{i+1}. {feature}")
            except Exception as e:
                print(f"Error parsing feature_names: {str(e)}")
    else:
        print("\nNo USD_CHF entry in selected_features_per_instrument")
        
    # Get a list of all instruments in the database
    sql_instruments = "SELECT DISTINCT instrument FROM selected_features_per_instrument"
    instruments = pd.read_sql_query(sql_instruments, conn)
    print("\nInstruments in selected_features_per_instrument:")
    print(instruments)

if __name__ == "__main__":
    check_feature_names() 