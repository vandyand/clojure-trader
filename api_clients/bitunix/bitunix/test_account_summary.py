"""
Test script for account summary functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitunix import BitUnixClient, AccountSummary

def main():
    print("Testing Account Summary Functionality")
    print("=" * 60)
    
    client = BitUnixClient()
    
    if client.public_only:
        print("ERROR: API keys not configured. Cannot test account summary.")
        return
    
    try:
        # Get account summary for USDT (default)
        print("\nFetching account summary for USDT...")
        summary: AccountSummary = client.get_account_summary()
        
        print("\n" + "-" * 40)
        print("ACCOUNT SUMMARY")
        print("-" * 40)
        print(f"Total Balance:        ${summary.total_balance:,.4f}")
        print(f"Total Available:      ${summary.total_available:,.4f}")
        print(f"Total Frozen:         ${summary.total_frozen:,.4f}")
        print(f"Total Margin:         ${summary.total_margin:,.4f}")
        print(f"Total Unrealized PNL: ${summary.total_unrealized_pnl:,.4f}")
        print("-" * 40)
        print(f"TOTAL EQUITY:         ${summary.total_equity:,.4f}")
        print("-" * 40)
        
        if summary.balances:
            print("\nIndividual Coin Balances:")
            for balance in summary.balances:
                balance_amount = balance.available + balance.frozen + balance.margin
                if balance_amount > 0 or balance.cross_unrealized_pnl != 0 or balance.isolation_unrealized_pnl != 0:
                    print(f"\n  {balance.margin_coin}:")
                    print(f"    Balance: {balance_amount:,.4f}")
                    print(f"    Available: {balance.available:,.4f}")
                    print(f"    Frozen: {balance.frozen:,.4f}")
                    print(f"    Margin: {balance.margin:,.4f}")
                    if balance.cross_unrealized_pnl != 0:
                        print(f"    Cross Unrealized PNL: {balance.cross_unrealized_pnl:,.4f}")
                    if balance.isolation_unrealized_pnl != 0:
                        print(f"    Isolation Unrealized PNL: {balance.isolation_unrealized_pnl:,.4f}")
        
        # Example: Test with multiple coins
        print("\n\nFetching account summary for multiple coins (USDT, BTC, ETH)...")
        multi_summary = client.get_account_summary(margin_coins=['USDT', 'BTC', 'ETH'])
        
        print("\n" + "-" * 40)
        print("MULTI-COIN ACCOUNT SUMMARY")
        print("-" * 40)
        print(f"Total Equity (All Coins): ${multi_summary.total_equity:,.4f}")
        print(f"Number of Coins: {len(multi_summary.balances)}")
        
        # Example: Position sizing calculation
        print("\n\nPOSITION SIZING EXAMPLE:")
        print("-" * 40)
        risk_percentage = 1.0  # 1% risk per trade
        position_size_value = summary.total_equity * (risk_percentage / 100)
        print(f"With {risk_percentage}% risk on ${summary.total_equity:,.4f} equity:")
        print(f"Maximum position size: ${position_size_value:,.4f}")
        
        # If BTC price is $100,000
        btc_price = 100000
        position_size_btc = position_size_value / btc_price
        print(f"At BTC price of ${btc_price:,}, that's {position_size_btc:.6f} BTC")
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    main() 