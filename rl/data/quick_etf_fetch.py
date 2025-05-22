#!/usr/bin/env python3
import os
import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Set up basic logging to console
import logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("quick_etf_fetch")

def fetch_etf_data(symbol, period="1mo"):
    """
    Simple function to fetch ETF data using yfinance without pandas_ta
    
    Args:
        symbol: ETF symbol (e.g., 'SPY')
        period: Time period (e.g., '1d', '1mo', '3mo', '1y')
        
    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        logger.info(f"Fetching data for {symbol} (period: {period})")
        
        # Create ticker object
        ticker = yf.Ticker(symbol)
        
        # Fetch historical data
        df = ticker.history(period=period)
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return None
        
        # Standardize column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Fill any missing values
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        logger.info(f"Successfully fetched {len(df)} records for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None

def fetch_multiple_etfs(symbols, period="1mo"):
    """
    Fetch data for multiple ETF symbols
    
    Args:
        symbols: List of ETF symbols
        period: Time period
        
    Returns:
        Dictionary of symbol -> DataFrame
    """
    results = {}
    
    for symbol in symbols:
        df = fetch_etf_data(symbol, period)
        if df is not None:
            results[symbol] = df
    
    return results

def calculate_basic_features(df):
    """
    Calculate basic features without using pandas_ta
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    features = pd.DataFrame(index=df.index)
    
    # Calculate basic features
    # Moving averages
    features['sma_20'] = df['close'].rolling(window=20).mean()
    features['sma_50'] = df['close'].rolling(window=50).mean()
    
    # Volatility
    features['std_20'] = df['close'].rolling(window=20).std()
    
    # Returns
    features['daily_return'] = df['close'].pct_change()
    features['weekly_return'] = df['close'].pct_change(periods=5)
    
    # Fill NaN values
    features = features.fillna(method='bfill').fillna(0)
    
    return features

def save_to_file(data, filename):
    """Save data to JSON file"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs('etf_data', exist_ok=True)
        
        # Save to file
        with open(os.path.join('etf_data', filename), 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        logger.info(f"Saved data to {filename}")
        
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def main():
    """Main function to fetch ETF data"""
    # List of common ETFs
    etfs = ["SPY", "QQQ", "IWM", "GLD"]
    
    # Fetch data
    data = fetch_multiple_etfs(etfs, period="1mo")
    
    # Calculate features and save results
    results = {}
    for symbol, df in data.items():
        features = calculate_basic_features(df)
        
        # Add to results
        results[symbol] = {
            "last_price": float(df['close'].iloc[-1]),
            "daily_change_pct": float(df['close'].pct_change().iloc[-1] * 100),
            "ma_20": float(features['sma_20'].iloc[-1]),
            "ma_50": float(features['sma_50'].iloc[-1]),
            "volatility": float(features['std_20'].iloc[-1]),
            "timestamp": datetime.now().isoformat()
        }
    
    # Save results
    save_to_file(results, "etf_summary.json")
    
    return results

if __name__ == "__main__":
    main() 