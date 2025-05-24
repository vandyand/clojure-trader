"""
Example usage of the Bitunix API integration.

This script demonstrates how to:
1. Fetch historical candlestick data
2. Get account information
3. Check open positions
4. Place and manage orders (limit/market with TP/SL)
5. Monitor and cancel orders
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitunix import (
    BitUnixClient, Candlestick, AccountBalance, PositionInfo, AccountSummary,
    OrderResponse, OrderInfo, OrderSide, OrderType, StopType, TimeInForce
)
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
            
        return summary
            
    except Exception as e:
        print(f"Error fetching account balance: {e}")
        return None


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
            
        return positions
            
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []


def demonstrate_order_placement():
    """Example: Demonstrate order placement with TP/SL."""
    print(f"\n{'='*60}")
    print(f"DEMONSTRATING ORDER PLACEMENT")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    if client.public_only:
        print("\nNote: API keys not configured. Order management requires authentication.")
        return None
    
    try:
        print("\n📝 EXAMPLE: Placing a limit order with Take Profit and Stop Loss")
        print("⚠️  Note: This example uses a limit order below market price, so it won't execute immediately.")
        
        # Get current market price context (using example prices)
        current_btc_price = 95000  # Example current BTC price
        order_price = current_btc_price - 1000  # Limit order below market
        take_profit_price = current_btc_price + 2000  # TP above market
        stop_loss_price = current_btc_price - 2000  # SL below market
        
        print(f"\nOrder Parameters:")
        print(f"- Symbol: BTCUSDT")
        print(f"- Side: BUY")
        print(f"- Type: LIMIT")
        print(f"- Quantity: 0.001 BTC")
        print(f"- Price: ${order_price:,} (below current market)")
        print(f"- Take Profit: ${take_profit_price:,}")
        print(f"- Stop Loss: ${stop_loss_price:,}")
        
        # Place the order
        order_response: OrderResponse = client.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY.value,
            order_type=OrderType.LIMIT.value,
            qty="0.001",
            price=str(order_price),
            effect=TimeInForce.GTC.value,
            tp_price=str(take_profit_price),
            tp_stop_type=StopType.LAST_PRICE.value,
            tp_order_type=OrderType.MARKET.value,
            sl_price=str(stop_loss_price),
            sl_stop_type=StopType.LAST_PRICE.value,
            sl_order_type=OrderType.MARKET.value
        )
        
        print(f"\n✅ Order placed successfully!")
        print(f"Order ID: {order_response.order_id}")
        print(f"Client ID: {order_response.client_id}")
        
        return order_response.order_id
        
    except Exception as e:
        print(f"❌ Error placing order: {e}")
        return None


def demonstrate_order_management(order_id: str):
    """Example: Demonstrate order management operations."""
    print(f"\n{'='*60}")
    print(f"DEMONSTRATING ORDER MANAGEMENT")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    try:
        # 1. Get order detail
        print(f"\n1️⃣ Getting order details...")
        order_detail: OrderInfo = client.get_order_detail(order_id)
        
        if order_detail:
            print(f"✅ Order found:")
            print(f"   Status: {order_detail.status}")
            print(f"   Price: ${order_detail.price:,.2f}")
            print(f"   Quantity: {order_detail.qty}")
            print(f"   Filled: {order_detail.filled_qty}")
        
        # 2. Modify the order
        print(f"\n2️⃣ Modifying order price...")
        modified_response = client.modify_order(
            order_id=order_id,
            price="94500",  # New price
            tp_price="98500",  # New take profit
            sl_price="91500"   # New stop loss
        )
        print(f"✅ Order modified successfully!")
        
        # 3. Get updated order detail
        print(f"\n3️⃣ Getting updated order details...")
        updated_order = client.get_order_detail(order_id)
        if updated_order:
            print(f"✅ Updated order:")
            print(f"   New Price: ${updated_order.price:,.2f}")
            print(f"   New TP: ${updated_order.tp_price:,.2f}")
            print(f"   New SL: ${updated_order.sl_price:,.2f}")
        
        # 4. Cancel the order
        print(f"\n4️⃣ Cancelling order...")
        cancel_response = client.cancel_order(
            symbol="BTCUSDT",
            order_id=order_id
        )
        
        if cancel_response.success_list:
            print(f"✅ Order cancelled successfully!")
        else:
            print(f"❌ Failed to cancel order: {cancel_response.failure_list}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in order management: {e}")
        return False


def display_pending_orders():
    """Example: Display current pending orders."""
    print(f"\n{'='*60}")
    print(f"FETCHING PENDING ORDERS")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    if client.public_only:
        print("\nNote: API keys not configured. Order management requires authentication.")
        return
    
    try:
        # Get pending orders for BTCUSDT
        pending_orders: List[OrderInfo] = client.get_pending_orders(symbol="BTCUSDT")
        
        if pending_orders:
            print(f"\nFound {len(pending_orders)} pending BTCUSDT orders:")
            print(f"\n{'Order ID':<20} {'Side':<6} {'Type':<8} {'Qty':<12} {'Price':<12} {'Status':<15}")
            print("-" * 85)
            
            for order in pending_orders:
                price_str = f"${order.price:,.2f}" if order.price else "Market"
                print(f"{order.order_id[:18]:<20} {order.side:<6} {order.order_type:<8} "
                      f"{order.qty:<12.4f} {price_str:<12} {order.status:<15}")
        else:
            print("No pending orders found for BTCUSDT.")
            
    except Exception as e:
        print(f"Error fetching pending orders: {e}")


def display_order_history():
    """Example: Display recent order history."""
    print(f"\n{'='*60}")
    print(f"FETCHING ORDER HISTORY")
    print(f"{'='*60}")
    
    client = BitUnixClient()
    
    if client.public_only:
        print("\nNote: API keys not configured. Order management requires authentication.")
        return
    
    try:
        # Get recent order history
        order_history: List[OrderInfo] = client.get_order_history(
            symbol="BTCUSDT",
            page=1,
            page_size=5
        )
        
        if order_history:
            print(f"\nRecent {len(order_history)} BTCUSDT orders:")
            print(f"\n{'Order ID':<20} {'Side':<6} {'Type':<8} {'Qty':<12} {'Status':<15} {'Avg Price':<12}")
            print("-" * 95)
            
            for order in order_history:
                avg_price_str = f"${order.avg_price:,.2f}" if order.avg_price else "N/A"
                print(f"{order.order_id[:18]:<20} {order.side:<6} {order.order_type:<8} "
                      f"{order.qty:<12.4f} {order.status:<15} {avg_price_str:<12}")
        else:
            print("No order history found for BTCUSDT.")
            
    except Exception as e:
        print(f"Error fetching order history: {e}")


def main():
    """Main function demonstrating various API features."""
    print("Bitunix API Integration - Complete Example Usage")
    print("=" * 60)
    
    # Example 1: Fetch candlestick data (public endpoint)
    display_candlesticks(symbol="BTCUSDT", interval="1h", limit=5)
    
    # Example 2: Get account information (requires API keys)
    account_summary = display_account_info()
    
    # Example 3: Get open positions (requires API keys)
    positions = display_positions()
    
    # Example 4: Display pending orders
    display_pending_orders()
    
    # Example 5: Display order history
    display_order_history()
    
    # Example 6: Order placement and management (requires API keys)
    client = BitUnixClient()
    if not client.public_only:
        print(f"\n{'='*60}")
        print("ORDER MANAGEMENT DEMONSTRATION")
        print(f"{'='*60}")
        print("⚠️  The following examples involve placing real orders!")
        print("   - Limit orders are placed below market price (safe)")
        print("   - Orders will be cancelled automatically")
        print("   - Use small amounts for testing")
        
        # Place a test order
        order_id = demonstrate_order_placement()
        
        if order_id:
            # Wait for order to be processed
            time.sleep(2)
            
            # Demonstrate order management
            demonstrate_order_management(order_id)
    
    # Display summary
    print(f"\n{'='*60}")
    print("EXAMPLE SUMMARY")
    print(f"{'='*60}")
    
    if account_summary:
        print(f"💰 Account Equity: ${account_summary.total_equity:,.2f}")
        print(f"📊 Available Balance: ${account_summary.total_available:,.2f}")
    
    if positions:
        total_pnl = sum(pos.unrealized_pnl for pos in positions)
        print(f"📈 Open Positions: {len(positions)}")
        print(f"💹 Total Unrealized PNL: ${total_pnl:,.2f}")
    
    print(f"\n🎯 Key Features Demonstrated:")
    print(f"   ✅ Market data (candlesticks)")
    print(f"   ✅ Account information and summary")
    print(f"   ✅ Position monitoring")
    if not client.public_only:
        print(f"   ✅ Order placement with TP/SL")
        print(f"   ✅ Order modification and cancellation")
        print(f"   ✅ Order history and pending orders")
    else:
        print(f"   ⚠️  Order management (requires API keys)")
    
    print(f"\n{'='*60}")
    print("Example completed! 🚀")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 