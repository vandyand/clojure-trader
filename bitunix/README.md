# Bitunix API Integration

This directory contains the Python implementation for integrating with the Bitunix cryptocurrency broker API.

## Features

The integration supports the following functionalities:

1. **Fetch Historic Candlestick Data:** Retrieve historical price and volume data for various cryptocurrencies.
2. **Get Account Information:** Access account balances, total equity, and comprehensive account statistics.
3. **Get Current Positions:** Fetch current open positions with detailed information.
4. **Account Summary & Total Value:** Calculate total account equity for position sizing and risk management.
5. **Post Orders:** Programmatically place, modify, and cancel orders to manage position sizes. _(Coming soon)_

## Project Structure

```
bitunix/
├── auth.py              # Authentication and signature generation
├── models.py            # Data structures (NamedTuples)
├── client.py            # Main API client
├── endpoints/           # Endpoint-specific implementations
│   ├── __init__.py
│   ├── market.py        # Market data endpoints
│   ├── account.py       # Account-related endpoints
│   └── position.py      # Position-related endpoints
├── example_usage.py     # Example usage script
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
from bitunix import BitUnixClient

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

### Running the Example Script

A comprehensive example script is provided:

```bash
python example_usage.py
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

# Run unit tests
python -m unittest test_client.py
```

## Error Handling

The client includes built-in error handling for:

- Network errors
- API errors (with error codes and messages)
- Authentication failures
- JSON parsing errors

Always wrap API calls in try-except blocks for production use.
