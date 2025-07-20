"""
ETF data fetching module using yfinance for the crypto RL system.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def fetch_historical_etf_data(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    period: str = "2y"
) -> Optional[pd.DataFrame]:
    """
    Fetch historical ETF data using yfinance.
    
    Args:
        symbol: ETF symbol (e.g., "SPY", "QQQ")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        period: Period if start_date/end_date not provided (default: "2y")
        
    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        # Create ticker object
        ticker = yf.Ticker(symbol)
        
        # Fetch historical data
        if start_date and end_date:
            df = ticker.history(start=start_date, end=end_date)
        else:
            df = ticker.history(period=period)
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return None
        
        # Ensure we have the required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns for {symbol}: {missing_columns}")
            return None
        
        # Clean up the data
        df = df[required_columns]
        df = df.dropna()
        
        # Convert to lowercase column names for consistency
        df.columns = df.columns.str.lower()
        
        logger.info(f"Fetched {len(df)} rows for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching ETF data for {symbol}: {e}")
        return None

def fetch_latest_etf_price(symbol: str) -> Optional[float]:
    """
    Fetch the latest price for an ETF.
    
    Args:
        symbol: ETF symbol
        
    Returns:
        Latest close price or None if error
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Try to get the latest price from info
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            return float(info['regularMarketPrice'])
        
        # Fallback: get the last close price from recent history
        df = ticker.history(period="1d")
        if not df.empty:
            return float(df['Close'].iloc[-1])
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching latest price for {symbol}: {e}")
        return None

def fetch_multiple_etfs(
    symbols: list,
    start_date: str = None,
    end_date: str = None,
    period: str = "2y"
) -> Dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple ETFs.
    
    Args:
        symbols: List of ETF symbols
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        period: Period if start_date/end_date not provided
        
    Returns:
        Dictionary mapping symbols to DataFrames
    """
    results = {}
    
    for symbol in symbols:
        logger.info(f"Fetching data for {symbol}...")
        df = fetch_historical_etf_data(symbol, start_date, end_date, period)
        if df is not None:
            results[symbol] = df
        else:
            logger.warning(f"Failed to fetch data for {symbol}")
    
    return results

def get_etf_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get basic information about an ETF.
    
    Args:
        symbol: ETF symbol
        
    Returns:
        Dictionary with ETF information or None if error
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Extract relevant information
        etf_info = {
            'symbol': symbol,
            'name': info.get('longName', ''),
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
            'market_cap': info.get('marketCap', 0),
            'volume': info.get('volume', 0),
            'avg_volume': info.get('averageVolume', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 0),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0)
        }
        
        return etf_info
        
    except Exception as e:
        logger.error(f"Error fetching ETF info for {symbol}: {e}")
        return None

def main():
    """Test the ETF data fetching functionality"""
    # Test symbols
    test_symbols = ["SPY", "QQQ", "GLD", "TLT"]
    
    print("Testing ETF data fetching...")
    
    for symbol in test_symbols:
        print(f"\n{symbol}:")
        
        # Get basic info
        info = get_etf_info(symbol)
        if info:
            print(f"  Name: {info['name']}")
            print(f"  Sector: {info['sector']}")
            print(f"  Market Cap: ${info['market_cap']:,.0f}")
        
        # Get historical data
        df = fetch_historical_etf_data(symbol, period="1mo")
        if df is not None:
            print(f"  Data shape: {df.shape}")
            print(f"  Latest close: ${df['close'].iloc[-1]:.2f}")
            print(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
        
        # Get latest price
        latest_price = fetch_latest_etf_price(symbol)
        if latest_price:
            print(f"  Latest price: ${latest_price:.2f}")

if __name__ == "__main__":
    main() 