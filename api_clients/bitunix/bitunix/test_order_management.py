"""
Test script for order management functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitunix import (
    BitUnixClient, OrderResponse, OrderInfo, CancelOrderResponse,
    OrderSide, OrderType, StopType, TimeInForce
)
import time


def display_order_info(order: OrderInfo, title: str = "Order Info"):
    """Display formatted order information."""
    print(f"\n{'-' * 20} {title} {'-' * 20}")
    print(f"Order ID: {order.order_id}")
    print(f"Client ID: {order.client_id}")
    print(f"Symbol: {order.symbol}")
    print(f"Side: {order.side}")
    print(f"Type: {order.order_type}")
    print(f"Quantity: {order.qty}")
    if order.price:
        print(f"Price: ${order.price:,.2f}")
    print(f"Filled: {order.filled_qty}")
    print(f"Remaining: {order.remaining_qty}")
    print(f"Status: {order.status}")
    if order.avg_price:
        print(f"Avg Price: ${order.avg_price:,.2f}")
    if order.tp_price:
        print(f"Take Profit: ${order.tp_price:,.2f} ({order.tp_order_type})")
    if order.sl_price:
        print(f"Stop Loss: ${order.sl_price:,.2f} ({order.sl_order_type})")
    print("-" * 60)


def test_place_limit_order(client: BitUnixClient):
    """Test placing a limit order with TP/SL."""
    print(f"\n{'='*60}")
    print("TESTING LIMIT ORDER PLACEMENT WITH TP/SL")
    print(f"{'='*60}")
    
    try:
        # Place a small limit buy order with take profit and stop loss
        current_btc_price = 95000  # Approximate current price for example
        buy_price = current_btc_price - 1000  # Buy below market
        take_profit_price = current_btc_price + 2000  # TP above market
        stop_loss_price = current_btc_price - 2000  # SL below market
        
        order_response = client.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY.value,
            order_type=OrderType.LIMIT.value,
            qty="0.001",  # Small amount for testing
            price=str(buy_price),
            effect=TimeInForce.GTC.value,
            tp_price=str(take_profit_price),
            tp_stop_type=StopType.LAST_PRICE.value,
            tp_order_type=OrderType.MARKET.value,
            sl_price=str(stop_loss_price),
            sl_stop_type=StopType.LAST_PRICE.value,
            sl_order_type=OrderType.MARKET.value
        )
        
        print(f"✅ Order placed successfully!")
        print(f"Order ID: {order_response.order_id}")
        print(f"Client ID: {order_response.client_id}")
        
        return order_response.order_id
        
    except Exception as e:
        print(f"❌ Error placing order: {e}")
        return None


def test_place_market_order(client: BitUnixClient):
    """Test placing a market order (be careful with real funds!)."""
    print(f"\n{'='*60}")
    print("TESTING MARKET ORDER PLACEMENT (Commented out for safety)")
    print(f"{'='*60}")
    
    print("⚠️  Market order testing is commented out to avoid accidental trades.")
    print("   Uncomment and modify the code below to test market orders with small amounts.")
    
    # UNCOMMENT AND MODIFY FOR TESTING (USE VERY SMALL AMOUNTS!)
    # try:
    #     order_response = client.place_order(
    #         symbol="BTCUSDT",
    #         side=OrderSide.BUY.value,
    #         order_type=OrderType.MARKET.value,
    #         qty="0.0001",  # Very small amount
    #         tp_price="100000",  # Take profit
    #         sl_price="90000"   # Stop loss
    #     )
    #     
    #     print(f"✅ Market order placed!")
    #     print(f"Order ID: {order_response.order_id}")
    #     return order_response.order_id
    #     
    # except Exception as e:
    #     print(f"❌ Error placing market order: {e}")
    
    return None


def test_get_pending_orders(client: BitUnixClient):
    """Test getting pending orders."""
    print(f"\n{'='*60}")
    print("TESTING GET PENDING ORDERS")
    print(f"{'='*60}")
    
    try:
        # Get all pending orders
        all_orders = client.get_pending_orders()
        
        print(f"Found {len(all_orders)} pending orders across all symbols.")
        
        # Get BTCUSDT specific orders
        btc_orders = client.get_pending_orders(symbol="BTCUSDT")
        
        print(f"Found {len(btc_orders)} pending BTCUSDT orders.")
        
        for i, order in enumerate(btc_orders[:3], 1):  # Show up to 3 orders
            display_order_info(order, f"Pending Order #{i}")
        
        return btc_orders
        
    except Exception as e:
        print(f"❌ Error getting pending orders: {e}")
        return []


def test_modify_order(client: BitUnixClient, order_id: str):
    """Test modifying an existing order."""
    print(f"\n{'='*60}")
    print("TESTING ORDER MODIFICATION")
    print(f"{'='*60}")
    
    try:
        # Modify the order price and TP/SL levels
        modified_response = client.modify_order(
            order_id=order_id,
            price="94500",  # New price
            tp_price="98000",  # New take profit
            sl_price="92000"   # New stop loss
        )
        
        print(f"✅ Order modified successfully!")
        print(f"Modified Order ID: {modified_response.order_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error modifying order: {e}")
        return False


def test_get_order_detail(client: BitUnixClient, order_id: str):
    """Test getting detailed order information."""
    print(f"\n{'='*60}")
    print("TESTING GET ORDER DETAIL")
    print(f"{'='*60}")
    
    try:
        order_detail = client.get_order_detail(order_id)
        
        if order_detail:
            display_order_info(order_detail, "Order Detail")
            return True
        else:
            print("❌ Order not found or error retrieving details.")
            return False
            
    except Exception as e:
        print(f"❌ Error getting order detail: {e}")
        return False


def test_cancel_order(client: BitUnixClient, order_id: str):
    """Test cancelling an order."""
    print(f"\n{'='*60}")
    print("TESTING ORDER CANCELLATION")
    print(f"{'='*60}")
    
    try:
        cancel_response = client.cancel_order(
            symbol="BTCUSDT",
            order_id=order_id
        )
        
        print(f"Cancel Response:")
        print(f"✅ Successfully cancelled: {len(cancel_response.success_list)} orders")
        print(f"❌ Failed to cancel: {len(cancel_response.failure_list)} orders")
        
        if cancel_response.success_list:
            for success in cancel_response.success_list:
                print(f"   Cancelled Order ID: {success.get('orderId', 'N/A')}")
        
        if cancel_response.failure_list:
            for failure in cancel_response.failure_list:
                print(f"   Failed Order ID: {failure.get('orderId', 'N/A')} - {failure.get('errorMsg', 'Unknown error')}")
        
        return len(cancel_response.success_list) > 0
        
    except Exception as e:
        print(f"❌ Error cancelling order: {e}")
        return False


def test_order_history(client: BitUnixClient):
    """Test getting order history."""
    print(f"\n{'='*60}")
    print("TESTING ORDER HISTORY")
    print(f"{'='*60}")
    
    try:
        # Get recent order history for BTCUSDT
        history = client.get_order_history(
            symbol="BTCUSDT",
            page=1,
            page_size=10
        )
        
        print(f"Found {len(history)} orders in history.")
        
        for i, order in enumerate(history[:3], 1):  # Show up to 3 recent orders
            display_order_info(order, f"Historical Order #{i}")
        
        return len(history)
        
    except Exception as e:
        print(f"❌ Error getting order history: {e}")
        return 0


def main():
    """Main function to test order management features."""
    print("Bitunix Order Management Testing")
    print("=" * 60)
    
    client = BitUnixClient()
    
    if client.public_only:
        print("❌ ERROR: API keys not configured. Order management requires authentication.")
        return
    
    print("🔐 Authentication: ✅ API keys configured")
    
    # Enable debug mode for detailed logging
    from bitunix import auth
    auth.DEBUG_SIGNATURE = True
    
    # Test 1: Get current pending orders
    pending_orders = test_get_pending_orders(client)
    
    # Test 2: Get order history
    history_count = test_order_history(client)
    
    # Test 3: Place a limit order (safe - won't execute immediately)
    placed_order_id = test_place_limit_order(client)
    
    if placed_order_id:
        # Wait a moment for order to be processed
        time.sleep(2)
        
        # Test 4: Get order detail
        test_get_order_detail(client, placed_order_id)
        
        # Test 5: Modify the order
        if test_modify_order(client, placed_order_id):
            time.sleep(2)
            
            # Test 6: Get updated order detail
            test_get_order_detail(client, placed_order_id)
        
        # Test 7: Cancel the order
        test_cancel_order(client, placed_order_id)
    
    # Test 8: Market order (commented out for safety)
    test_place_market_order(client)
    
    print(f"\n{'='*60}")
    print("ORDER MANAGEMENT TESTING COMPLETED")
    print(f"{'='*60}")
    print("Summary:")
    print(f"- Found {len(pending_orders)} pending orders")
    print(f"- Found {history_count} orders in history")
    if placed_order_id:
        print(f"- Successfully tested order lifecycle with ID: {placed_order_id}")
    else:
        print("- Order placement test failed")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("- This script uses real API calls with real funds!")
    print("- Always test with small amounts first")
    print("- Market orders execute immediately - use with caution")
    print("- Review all orders in your Bitunix dashboard")


if __name__ == "__main__":
    main() 