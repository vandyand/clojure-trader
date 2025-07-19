#!/usr/bin/env python3
"""
Script to query Bitunix API for available USDT-margined perpetual futures symbols and their metrics.
"""
import requests
import json
from typing import List, Dict
from datetime import datetime

def fetch_futures_symbols() -> List[Dict]:
    """Fetch available USDT-margined perpetual futures symbols and their metrics from Bitunix API."""
    # First get all trading pairs
    pairs_endpoint = "https://fapi.bitunix.com/api/v1/futures/market/trading_pairs"
    pairs_response = requests.get(pairs_endpoint)
    
    if pairs_response.status_code != 200:
        print(f"Error fetching trading pairs: {pairs_response.status_code} - {pairs_response.text}")
        return []
    
    pairs_data = pairs_response.json()
    if not pairs_data.get('data'):
        print("No trading pairs data found")
        return []
    
    # Filter for USDT-margined perpetual futures that are OPEN
    futures_pairs = [
        item for item in pairs_data.get('data', [])
        if item.get('quote') == 'USDT' and item.get('symbolStatus') == 'OPEN'
    ]
    
    # Get 24h ticker data for volume information
    ticker_endpoint = "https://fapi.bitunix.com/api/v1/futures/market/tickers"
    ticker_response = requests.get(ticker_endpoint)
    
    if ticker_response.status_code != 200:
        print(f"Error fetching tickers: {ticker_response.status_code} - {ticker_response.text}")
        return futures_pairs
    
    ticker_data = ticker_response.json()
    if not ticker_data.get('data'):
        print("No ticker data found")
        return futures_pairs
    
    # Create a map of symbol to ticker data
    ticker_map = {item['symbol']: item for item in ticker_data.get('data', [])}
    
    # Enrich futures pairs with ticker data
    for pair in futures_pairs:
        symbol = pair['symbol']
        if symbol in ticker_map:
            pair.update({
                'volume_24h': float(ticker_map[symbol].get('volume', 0)),
                'quote_volume_24h': float(ticker_map[symbol].get('quoteVolume', 0)),
                'price_change_24h': float(ticker_map[symbol].get('priceChange', 0)),
                'price_change_percent_24h': float(ticker_map[symbol].get('priceChangePercent', 0)),
                'last_price': float(ticker_map[symbol].get('lastPrice', 0))
            })
    
    return futures_pairs

if __name__ == "__main__":
    symbols = fetch_futures_symbols()
    
    # Sort by 24h quote volume (USDT volume)
    sorted_by_volume = sorted(
        symbols,
        key=lambda x: x.get('quote_volume_24h', 0),
        reverse=True
    )
    
    print(f"\nFound {len(sorted_by_volume)} USDT-margined perpetual futures pairs")
    print("\nTop 20 by 24h Volume (USDT):")
    print("=" * 100)
    print(f"{'Symbol':<12} {'Last Price':<12} {'24h Volume (USDT)':<20} {'24h % Change':<12} {'Status':<10}")
    print("-" * 100)
    
    for pair in sorted_by_volume[:20]:
        print(
            f"{pair['symbol']:<12} "
            f"{pair.get('last_price', 0):<12.4f} "
            f"{pair.get('quote_volume_24h', 0):<20,.0f} "
            f"{pair.get('price_change_percent_24h', 0):<12.2f}% "
            f"{pair.get('symbolStatus', 'N/A'):<10}"
        ) 