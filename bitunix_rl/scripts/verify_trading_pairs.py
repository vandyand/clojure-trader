#!/usr/bin/env python3
"""
Script to verify which top market cap coins are available as USDT-margined perpetual futures on Bitunix.
"""
import requests
from typing import List, Dict, Set

# Top market cap coins (excluding stablecoins)
TOP_COINS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "HYPE", "SUI",
    "LINK", "AVAX", "XLM", "SHIB", "BCH", "LEO", "HBAR", "TON", "XMR", "LTC",
    "DOT", "BGB", "PEPE", "PI", "AAVE", "UNI", "TAO", "APT", "NEAR", "OKB"
]

def fetch_bitunix_pairs() -> Set[str]:
    """Fetch all available USDT-margined perpetual futures pairs from Bitunix."""
    endpoint = "https://fapi.bitunix.com/api/v1/futures/market/trading_pairs"
    response = requests.get(endpoint)
    
    if response.status_code != 200:
        print(f"Error fetching trading pairs: {response.status_code}")
        return set()
    
    data = response.json()
    if not data.get('data'):
        return set()
    
    # Filter for USDT-margined perpetual futures that are OPEN
    available_pairs = {
        item['symbol'].replace('USDT', '')
        for item in data.get('data', [])
        if item.get('quote') == 'USDT' 
        and item.get('symbolStatus') == 'OPEN'
    }
    
    return available_pairs

def main():
    """Main function to verify available trading pairs."""
    available_pairs = fetch_bitunix_pairs()
    
    print("\nVerifying top market cap coins against Bitunix perpetual futures:")
    print("=" * 60)
    print(f"{'Coin':<8} {'Available':<10} {'Symbol':<12}")
    print("-" * 60)
    
    available_count = 0
    for coin in TOP_COINS:
        is_available = coin in available_pairs
        if is_available:
            available_count += 1
        print(f"{coin:<8} {'✓' if is_available else '✗':<10} {coin + 'USDT' if is_available else 'N/A':<12}")
    
    print("\nSummary:")
    print(f"Total coins checked: {len(TOP_COINS)}")
    print(f"Available on Bitunix: {available_count}")
    print(f"Not available: {len(TOP_COINS) - available_count}")

if __name__ == "__main__":
    main() 