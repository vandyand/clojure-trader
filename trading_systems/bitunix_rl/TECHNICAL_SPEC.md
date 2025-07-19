# Bitunix RL Technical Specification

## 1. Bitunix API Integration

The project uses the existing Bitunix API client implementation from the `bitunix/` directory. This implementation provides a robust foundation for interacting with the Bitunix API, including:

### 1.1 Client Structure

```python
# From bitunix/client.py
class BitunixClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.bitunix.com"
        self.ws_url = "wss://ws.bitunix.com"
```

### 1.2 Available Endpoints

The existing client provides comprehensive coverage of Bitunix's API endpoints:

1. **Market Data**

   - OHLCV data (`/fapi/v1/klines`)
   - Order book depth (`/fapi/v1/depth`)
   - Recent trades (`/fapi/v1/trades`)
   - Funding rate information (`/fapi/v1/fundingRate`)

2. **Account Management**

   - Account information (`/fapi/v2/account`)
   - Position information (`/fapi/v2/positionRisk`)
   - Balance updates (`/fapi/v2/balance`)

3. **Order Management**
   - Place order (`/fapi/v1/order`)
   - Cancel order (`/fapi/v1/order`)
   - Query order (`/fapi/v1/order`)
   - Open orders (`/fapi/v1/openOrders`)

### 1.3 WebSocket Support

The client includes WebSocket functionality for real-time data:

```python
# From bitunix/client.py
async def subscribe_klines(self, symbol: str, interval: str):
    """
    Subscribe to candlestick data via WebSocket
    """
    subscription = {
        "method": "SUBSCRIBE",
        "params": [f"{symbol.lower()}@kline_{interval}"],
        "id": 1
    }
    await self.ws.send(json.dumps(subscription))
```

### 1.4 Error Handling

The client implements comprehensive error handling:

```python
# From bitunix/client.py
class BitunixAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Bitunix API Error {code}: {message}")
```

## 2. Perpetual Futures Mechanics

### 2.1 Funding Rate

```python
class FundingRateCalculator:
    def __init__(self, client: BitunixClient):
        self.client = client

    async def get_current_funding_rate(self, symbol: str) -> float:
        """
        Get current funding rate for a symbol
        """
        response = await self.client.get_funding_rate(symbol)
        return float(response['fundingRate'])

    def calculate_funding_payment(self, position_size: float,
                                funding_rate: float) -> float:
        """
        Calculate funding rate payment for a position
        """
        return position_size * funding_rate
```

### 2.2 Leverage and Margin

```python
class MarginCalculator:
    def __init__(self, client: BitunixClient):
        self.client = client

    async def set_leverage(self, symbol: str, leverage: int):
        """
        Set leverage for a symbol
        """
        await self.client.set_leverage(symbol, leverage)

    async def get_position_margin(self, symbol: str) -> float:
        """
        Get current position margin
        """
        position = await self.client.get_position(symbol)
        return float(position['positionAmt']) * float(position['entryPrice'])
```

### 2.3 Position Management

```python
class PositionManager:
    def __init__(self, client: BitunixClient):
        self.client = client
        self.positions = {}

    async def update_positions(self):
        """
        Update all position information
        """
        positions = await self.client.get_all_positions()
        for position in positions:
            if float(position['positionAmt']) != 0:
                self.positions[position['symbol']] = {
                    'size': float(position['positionAmt']),
                    'entry_price': float(position['entryPrice']),
                    'mark_price': float(position['markPrice']),
                    'unrealized_pnl': float(position['unRealizedProfit'])
                }
```

## 3. Data Structures

### 3.1 OHLCV Data

```python
@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    taker_buy_volume: float
    taker_buy_quote_volume: float

    @classmethod
    def from_bitunix_response(cls, data: List[Any]) -> 'Candle':
        """
        Create Candle instance from Bitunix API response
        """
        return cls(
            timestamp=int(data[0]),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            quote_volume=float(data[7]),
            trades=int(data[8]),
            taker_buy_volume=float(data[9]),
            taker_buy_quote_volume=float(data[10])
        )
```

### 3.2 Position Data

```python
@dataclass
class Position:
    symbol: str
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    realized_pnl: float
    funding_payments: float
    leverage: float
    margin_type: str
    liquidation_price: float

    @classmethod
    def from_bitunix_response(cls, data: Dict[str, Any]) -> 'Position':
        """
        Create Position instance from Bitunix API response
        """
        return cls(
            symbol=data['symbol'],
            size=float(data['positionAmt']),
            entry_price=float(data['entryPrice']),
            mark_price=float(data['markPrice']),
            unrealized_pnl=float(data['unRealizedProfit']),
            realized_pnl=float(data.get('realizedProfit', 0)),
            funding_payments=float(data.get('fundingFee', 0)),
            leverage=float(data['leverage']),
            margin_type=data['marginType'],
            liquidation_price=float(data['liquidationPrice'])
        )
```

## 4. Testing

### 4.1 Unit Tests

The existing Bitunix client includes comprehensive tests:

- `test_client.py`: Basic client functionality
- `test_candlesticks.py`: OHLCV data fetching
- `test_account_info.py`: Account information
- `test_order_management.py`: Order operations
- `test_debug_account.py`: Account debugging

### 4.2 Integration Tests

New integration tests to be added:

- Position management with funding rates
- Leverage and margin calculations
- Real-time data streaming
- End-to-end trading flow

### 4.3 Performance Tests

- API rate limiting compliance
- WebSocket message handling
- Database operations
- Feature calculation speed

## 5. Monitoring

### 5.1 Health Checks

- API connectivity
- WebSocket connection
- Database connection
- Position status
- Order execution

### 5.2 Metrics

- API response times
- WebSocket latency
- Order execution time
- Position PnL
- Funding rate payments
- Error rates

### 5.3 Alerts

- API errors
- WebSocket disconnections
- Position liquidation
- High funding rates
- Unusual price movements
