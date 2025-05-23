"""
Example usage of the Bitunix API integration.

This script demonstrates how to:
1. Fetch historical candlestick data
2. Get account information
3. Check open positions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitunix import BitUnixClient, Candlestick, AccountBalance, PositionInfo, AccountSummary
from typing import List
import time


def display_candlesticks(symbol: str, interval: str, limit: int = 5):
    """Example: Fetch and display candlestick data."""
    print(f"\n{'='*60}")
    print(f"FETCHING CANDLESTICK DATA")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    try:
        klines: List[Candlestick] = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        if klines:
            print(f"\nLatest {len(klines)} {interval} candles for {symbol}:")
            print(f"{'Time':<20} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12} {'Volume':<15}")
            print("-" * 95)
            
            for k in klines:
                time_str = time.strftime('%Y-%m-%d %H:%M', time.gmtime(k.open_time/1000))
                print(f"{time_str:<20} {k.open_price:<12.2f} {k.high_price:<12.2f} "
                      f"{k.low_price:<12.2f} {k.close_price:<12.2f} {k.volume:<15.4f}")
        else:
            print("No candlestick data available.")
            
    except Exception as e:
        print(f"Error fetching candlesticks: {e}")


def display_account_info():
    """Example: Fetch and display account balance and summary."""
    print(f"\n{'='*60}")
    print(f"FETCHING ACCOUNT INFORMATION")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    if client.public_only:
        print("\nNote: API keys not configured. Only public endpoints available.")
        return
    
    try:
        # Get account summary
        summary: AccountSummary = client.get_account_summary()
        
        print("\n" + "-" * 40)
        print("ACCOUNT SUMMARY")
        print("-" * 40)
        print(f"Total Equity:         ${summary.total_equity:,.2f}")
        print(f"Total Balance:        ${summary.total_balance:,.2f}")
        print(f"Total Available:      ${summary.total_available:,.2f}")
        print(f"Total Margin Used:    ${summary.total_margin:,.2f}")
        print(f"Total Unrealized PNL: ${summary.total_unrealized_pnl:,.2f}")
        print("-" * 40)
        
        # Show individual balances
        if summary.balances:
            print("\nDetailed Balances:")
            for balance in summary.balances:
                print(f"\nMargin Coin: {balance.margin_coin}")
                print(f"  Available: {balance.available:,.4f}")
                print(f"  Frozen: {balance.frozen:,.4f}")
                print(f"  Margin: {balance.margin:,.4f}")
                print(f"  Transferable: {balance.transfer:,.4f}")
                print(f"  Position Mode: {balance.position_mode}")
                if balance.cross_unrealized_pnl != 0:
                    print(f"  Cross Unrealized PNL: {balance.cross_unrealized_pnl:,.4f}")
                if balance.isolation_unrealized_pnl != 0:
                    print(f"  Isolation Unrealized PNL: {balance.isolation_unrealized_pnl:,.4f}")
                if balance.bonus != 0:
                    print(f"  Bonus: {balance.bonus:,.4f}")
        else:
            print("No account balance information available.")
            
    except Exception as e:
        print(f"Error fetching account balance: {e}")


def display_positions(symbol: str = None):
    """Example: Fetch and display open positions."""
    print(f"\n{'='*60}")
    print(f"FETCHING OPEN POSITIONS")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    if client.public_only:
        print("\nNote: API keys not configured. Only public endpoints available.")
        return
    
    try:
        # Fetch positions
        if symbol:
            print(f"\nFetching positions for {symbol}...")
            positions: List[PositionInfo] = client.get_open_positions(symbol=symbol)
        else:
            print("\nFetching all open positions...")
            positions: List[PositionInfo] = client.get_open_positions()
        
        if positions:
            print(f"\nFound {len(positions)} open position(s):")
            print(f"\n{'Symbol':<12} {'Side':<6} {'Size':<12} {'Entry Price':<12} "
                  f"{'Leverage':<10} {'Unrealized PNL':<15} {'Margin Type':<12}")
            print("-" * 95)
            
            for pos in positions:
                print(f"{pos.symbol:<12} {pos.position_side:<6} {pos.position_amt:<12.4f} "
                      f"{pos.entry_price:<12.2f} {pos.leverage:<10}x "
                      f"{pos.unrealized_pnl:<15.2f} {pos.margin_type:<12}")
        else:
            print("No open positions found.")
            
    except Exception as e:
        print(f"Error fetching positions: {e}")


def main():
    """Main function demonstrating various API features."""
    print("Bitunix API Integration - Example Usage")
    print("=" * 60)
    
    # Example 1: Fetch candlestick data (public endpoint)
    display_candlesticks(symbol="BTCUSDT", interval="1h", limit=5)
    
    # Example 2: Get account information (requires API keys)
    display_account_info()
    
    # Example 3: Get open positions (requires API keys)
    display_positions()
    
    # Example 4: Get positions for specific symbol
    display_positions(symbol="BTCUSDT")
    
    print(f"\n{'='*60}")
    print("Example completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 