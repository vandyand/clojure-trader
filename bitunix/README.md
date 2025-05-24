# Bitunix API Integration

This directory contains the Python implementation for integrating with the Bitunix cryptocurrency broker API.

## Features

The integration supports the following functionalities:

1. **Fetch Historic Candlestick Data:** Retrieve historical price and volume data for various cryptocurrencies.
2. **Get Account Information:** Access account balances, total equity, and comprehensive account statistics.
3. **Get Current Positions:** Fetch current open positions with detailed information.
4. **Account Summary & Total Value:** Calculate total account equity for position sizing and risk management.
5. **Complete Order Management:** Place, modify, and cancel orders with advanced features including Take Profit and Stop Loss.

## Project Structure

```
bitunix/
├── auth.py              # Authentication and signature generation
├── models.py            # Data structures (NamedTuples) and enums
├── client.py            # Main API client
├── endpoints/           # Endpoint-specific implementations
│   ├── __init__.py
│   ├── market.py        # Market data endpoints
│   ├── account.py       # Account-related endpoints
│   ├── position.py      # Position-related endpoints
│   └── order.py         # Order management endpoints
├── example_usage.py     # Comprehensive example script
├── test_*.py           # Test scripts
└── requirements.txt     # Python dependencies
```

## Installation

1. Set up a Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Authentication

This integration utilizes API key and secret key authentication. Ensure the following environment variables are set:

- `BITUNIX_API_KEY`
- `BITUNIX_SECRET_KEY`

You can set these in your shell or create a `.env` file in the project root:

```
BITUNIX_API_KEY=your_api_key_here
BITUNIX_SECRET_KEY=your_secret_key_here
```

## Usage

### Quick Start

```python
from bitunix import BitUnixClient, OrderSide, OrderType, StopType

# Initialize client
client = BitUnixClient()

# Fetch candlestick data (public endpoint)
klines = client.get_historical_klines(
    symbol="BTCUSDT",
    interval="1h",
    limit=10
)

# Get account balance (requires API keys)
balances = client.get_account_balance(margin_coin="USDT")

# Get open positions (requires API keys)
positions = client.get_open_positions()

# Place a limit order with TP/SL (requires API keys)
order_response = client.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY.value,
    order_type=OrderType.LIMIT.value,
    qty="0.001",
    price="94000",
    tp_price="97000",  # Take profit
    sl_price="92000"   # Stop loss
)
```

### Detailed Examples

#### 1. Fetching Historical Candlestick Data

```python
from bitunix import BitUnixClient
import time

client = BitUnixClient()

# Get last 24 hours of 15-minute candles
end_time = int(time.time() * 1000)  # Current time in ms
start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago

klines = client.get_historical_klines(
    symbol="BTCUSDT",
    interval="15m",
    start_time=start_time,
    end_time=end_time,
    limit=100
)

for kline in klines:
    print(f"Time: {kline.open_time}, "
          f"OHLC: {kline.open_price}/{kline.high_price}/{kline.low_price}/{kline.close_price}, "
          f"Volume: {kline.volume}")
```

#### 2. Getting Account Information and Total Equity

```python
from bitunix import BitUnixClient

client = BitUnixClient()

# Get comprehensive account summary
summary = client.get_account_summary()

print(f"Total Account Equity: ${summary.total_equity:,.2f}")
print(f"Total Balance: ${summary.total_balance:,.2f}")
print(f"Total Available: ${summary.total_available:,.2f}")
print(f"Total Unrealized PNL: ${summary.total_unrealized_pnl:,.2f}")

# Position sizing example - risk 1% of account
risk_percentage = 1.0
position_size = summary.total_equity * (risk_percentage / 100)
print(f"1% risk position size: ${position_size:,.2f}")

# Get summary for multiple coins
multi_summary = client.get_account_summary(margin_coins=['USDT', 'BTC', 'ETH'])
```

#### 3. Checking Open Positions

```python
from bitunix import BitUnixClient

client = BitUnixClient()

# Get all open positions
positions = client.get_open_positions()

# Get positions for specific symbol
btc_positions = client.get_open_positions(symbol="BTCUSDT")

for pos in positions:
    print(f"Symbol: {pos.symbol}, "
          f"Side: {pos.position_side}, "
          f"Size: {pos.position_amt}, "
          f"Entry: {pos.entry_price}, "
          f"PNL: {pos.unrealized_pnl}")
```

#### 4. Order Management

##### Placing Orders

```python
from bitunix import BitUnixClient, OrderSide, OrderType, StopType, TimeInForce

client = BitUnixClient()

# Place a limit buy order with Take Profit and Stop Loss
order_response = client.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY.value,
    order_type=OrderType.LIMIT.value,
    qty="0.001",
    price="94000",
    effect=TimeInForce.GTC.value,
    # Take Profit settings
    tp_price="97000",
    tp_stop_type=StopType.LAST_PRICE.value,
    tp_order_type=OrderType.MARKET.value,
    # Stop Loss settings
    sl_price="92000",
    sl_stop_type=StopType.LAST_PRICE.value,
    sl_order_type=OrderType.MARKET.value
)

print(f"Order placed: {order_response.order_id}")

# Place a market order (executes immediately!)
market_order = client.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY.value,
    order_type=OrderType.MARKET.value,
    qty="0.001",
    tp_price="97000",
    sl_price="92000"
)
```

##### Managing Orders

```python
# Get pending orders
pending_orders = client.get_pending_orders(symbol="BTCUSDT")
for order in pending_orders:
    print(f"Order: {order.order_id}, Status: {order.status}, Price: ${order.price}")

# Modify an existing order
client.modify_order(
    order_id=order_response.order_id,
    price="94500",  # New price
    tp_price="98000",  # New take profit
    sl_price="91500"   # New stop loss
)

# Get order details
order_detail = client.get_order_detail(order_response.order_id)
print(f"Order Status: {order_detail.status}")
print(f"Filled: {order_detail.filled_qty}/{order_detail.qty}")

# Cancel an order
cancel_response = client.cancel_order(
    symbol="BTCUSDT",
    order_id=order_response.order_id
)

if cancel_response.success_list:
    print("Order cancelled successfully!")

# Get order history
order_history = client.get_order_history(
    symbol="BTCUSDT",
    page=1,
    page_size=10
)
```

##### Advanced Order Features

```python
# Place order with custom client ID
custom_order = client.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY.value,
    order_type=OrderType.LIMIT.value,
    qty="0.001",
    price="94000",
    client_id="my_custom_order_123",
    effect=TimeInForce.IOC.value  # Immediate or Cancel
)

# Cancel multiple orders at once
cancel_response = client.cancel_orders(
    symbol="BTCUSDT",
    order_list=[
        {"orderId": "order1"},
        {"clientId": "my_custom_order_123"}
    ]
)

# Reduce-only order (only reduces position size)
reduce_order = client.place_order(
    symbol="BTCUSDT",
    side=OrderSide.SELL.value,
    order_type=OrderType.MARKET.value,
    qty="0.001",
    reduce_only=True
)
```

### Running the Example Script

A comprehensive example script is provided:

```bash
python example_usage.py
```

This script demonstrates all features including order management with safety measures.

### Order Management Testing

For comprehensive order management testing:

```bash
python test_order_management.py
```

⚠️ **Important:** This script places real orders! Review the code and use small amounts for testing.

## Available Data Types and Enums

### Order Management Enums

```python
from bitunix import OrderSide, OrderType, StopType, TimeInForce, OrderStatus

# Order sides
OrderSide.BUY        # "BUY"
OrderSide.SELL       # "SELL"

# Order types
OrderType.LIMIT      # "LIMIT"
OrderType.MARKET     # "MARKET"

# Stop types for TP/SL
StopType.MARK_PRICE  # "MARK_PRICE"
StopType.LAST_PRICE  # "LAST_PRICE"

# Time in force
TimeInForce.GTC      # "GTC" - Good Till Canceled
TimeInForce.IOC      # "IOC" - Immediate or Cancel
TimeInForce.FOK      # "FOK" - Fill or Kill
TimeInForce.POST_ONLY # "POST_ONLY" - Post Only

# Order status
OrderStatus.PENDING           # "PENDING"
OrderStatus.FILLED            # "FILLED"
OrderStatus.PARTIALLY_FILLED  # "PARTIALLY_FILLED"
OrderStatus.CANCELLED         # "CANCELLED"
OrderStatus.REJECTED          # "REJECTED"
```

## Available Intervals for Candlestick Data

- `1m` - 1 minute
- `5m` - 5 minutes
- `15m` - 15 minutes
- `30m` - 30 minutes
- `1h` - 1 hour
- `4h` - 4 hours
- `1d` - 1 day
- `1w` - 1 week
- `1M` - 1 month

## Order Management Features

### Supported Order Types

- **Limit Orders:** Orders with specified price levels
- **Market Orders:** Orders that execute immediately at current market price
- **Reduce-Only Orders:** Orders that only reduce existing position size
- **Orders with Take Profit/Stop Loss:** Automatic profit-taking and loss-limiting

### Take Profit and Stop Loss

- **Trigger Types:** MARK_PRICE or LAST_PRICE
- **Order Types:** LIMIT or MARKET execution when triggered
- **Flexible Configuration:** Different settings for TP and SL

### Time in Force Options

- **GTC (Good Till Canceled):** Order remains active until filled or cancelled
- **IOC (Immediate or Cancel):** Execute immediately or cancel unfilled portion
- **FOK (Fill or Kill):** Execute completely or cancel entire order
- **POST_ONLY:** Only add liquidity, never take liquidity

## Rate Limits

Be aware of Bitunix API rate limits:

- **Order Placement:** 10 requests/second per UID
- **Order Modification:** 10 requests/second per UID
- **Order Cancellation:** 5 requests/second per UID

## Safety Recommendations

### For Production Use

1. **Start Small:** Always test with small amounts first
2. **Use Limit Orders:** More control than market orders
3. **Set Stop Losses:** Protect against unexpected losses
4. **Monitor Rate Limits:** Implement appropriate delays between requests
5. **Error Handling:** Always wrap API calls in try-catch blocks
6. **Validate Parameters:** Check all order parameters before submission

### Example Safety Pattern

```python
try:
    # Validate account has sufficient balance
    summary = client.get_account_summary()
    if summary.total_available < minimum_balance:
        raise ValueError("Insufficient balance")

    # Place order with safety checks
    order_response = client.place_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY.value,
        order_type=OrderType.LIMIT.value,
        qty="0.001",  # Small amount
        price="94000",
        sl_price="92000"  # Always include stop loss
    )

    # Log successful order
    print(f"Order placed successfully: {order_response.order_id}")

except Exception as e:
    print(f"Order failed: {e}")
    # Handle error appropriately
```

## Roadmap

Refer to `ROADMAP.md` for a detailed list of development tasks and their current status.

## Testing

Run the test scripts to verify functionality:

```bash
# Test candlestick data fetching
python test_candlesticks.py

# Test account information fetching
python test_account_info.py

# Test account summary functionality
python test_account_summary.py

# Test order management (⚠️ uses real API)
python test_order_management.py

# Run unit tests
python -m unittest test_client.py
```

## Error Handling

The client includes built-in error handling for:

- Network errors
- API errors (with error codes and messages)
- Authentication failures
- JSON parsing errors
- Order validation errors

Always wrap API calls in try-except blocks for production use:

```python
try:
    order = client.place_order(...)
except ValueError as e:
    print(f"Invalid parameters: {e}")
except requests.exceptions.HTTPError as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Support

For issues with this integration:

1. Check the error messages and logs
2. Verify API credentials are correct
3. Ensure sufficient account balance
4. Review Bitunix API documentation
5. Test with small amounts first

For Bitunix-specific issues, consult their official documentation and support channels.
