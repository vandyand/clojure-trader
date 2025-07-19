"""
Data models for Bitunix API integration.
"""
from typing import NamedTuple, Optional
from enum import Enum


# Enums for order management
class OrderSide(Enum):
    """Order side direction."""
    BUY = "BUY"
    SELL = "SELL"


class TradeSide(Enum):
    """Trade side for position management."""
    OPEN = "OPEN"
    CLOSE = "CLOSE"


class OrderType(Enum):
    """Order type."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TimeInForce(Enum):
    """Order time in force."""
    GTC = "GTC"  # Good Till Canceled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    POST_ONLY = "POST_ONLY"  # Post Only


class StopType(Enum):
    """Stop trigger type for TP/SL."""
    MARK_PRICE = "MARK_PRICE"
    LAST_PRICE = "LAST_PRICE"


class Candlestick(NamedTuple):
    """Represents candlestick/kline data."""
    open_time: int  # Start time of the candle (Unix timestamp in ms)
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float      # Trading volume (base asset, e.g., BTC for BTCUSDT)
    quote_volume: float # Trading amount (quote asset, e.g., USDT for BTCUSDT)
    kline_type: Optional[str] = None # e.g., LAST_PRICE or MARK_PRICE


class AccountBalance(NamedTuple):
    """Represents account balance information."""
    margin_coin: str
    available: float # Available quantity
    frozen: float    # Locked quantity for orders
    margin: float    # Locked quantity for positions
    transfer: float  # Maximum transferable amount
    position_mode: str # ONE_WAY or HEDGE
    cross_unrealized_pnl: float
    isolation_unrealized_pnl: float
    bonus: float


class PositionInfo(NamedTuple):
    """Represents an open position."""
    symbol: str
    position_side: str # LONG or SHORT
    unrealized_pnl: float
    entry_price: float
    position_amt: float # Position amount
    initial_margin: float
    leverage: int
    margin_type: str # CROSS or ISOLATED
    # Additional fields from Bitunix API
    position_id: Optional[str] = None
    qty: Optional[float] = None
    entry_value: Optional[float] = None
    side: Optional[str] = None # Bitunix uses 'side' field
    margin_mode: Optional[str] = None # ISOLATION or CROSS
    position_mode: Optional[str] = None # ONE_WAY or HEDGE
    fee: Optional[float] = None
    funding: Optional[float] = None
    realized_pnl: Optional[float] = None
    liq_price: Optional[float] = None
    margin_rate: Optional[float] = None
    avg_open_price: Optional[float] = None
    ctime: Optional[int] = None
    mtime: Optional[int] = None


class AccountSummary(NamedTuple):
    """Represents account summary with total values."""
    total_balance: float  # Total wallet balance (available + frozen + margin)
    total_available: float  # Total available balance
    total_frozen: float  # Total frozen balance
    total_margin: float  # Total margin used
    total_unrealized_pnl: float  # Total unrealized PNL (cross + isolation)
    total_equity: float  # Total account equity (balance + unrealized PNL)
    balances: list  # List of AccountBalance objects for each coin


class OrderRequest(NamedTuple):
    """Request parameters for placing an order."""
    symbol: str
    side: str  # BUY or SELL
    order_type: str  # LIMIT or MARKET
    qty: str  # Amount in base coin
    price: Optional[str] = None  # Required for LIMIT orders
    trade_side: Optional[str] = None  # OPEN or CLOSE (required in hedge mode)
    position_id: Optional[str] = None  # Required when closing position
    effect: Optional[str] = "GTC"  # GTC, IOC, FOK, POST_ONLY
    client_id: Optional[str] = None  # Custom order ID
    reduce_only: Optional[bool] = False  # Whether to only reduce position
    # Take Profit parameters
    tp_price: Optional[str] = None
    tp_stop_type: Optional[str] = None  # MARK_PRICE or LAST_PRICE
    tp_order_type: Optional[str] = None  # LIMIT or MARKET
    tp_order_price: Optional[str] = None  # Required if tp_order_type is LIMIT
    # Stop Loss parameters
    sl_price: Optional[str] = None
    sl_stop_type: Optional[str] = None  # MARK_PRICE or LAST_PRICE
    sl_order_type: Optional[str] = None  # LIMIT or MARKET
    sl_order_price: Optional[str] = None  # Required if sl_order_type is LIMIT


class OrderResponse(NamedTuple):
    """Response from order placement."""
    order_id: str
    client_id: Optional[str] = None


class OrderInfo(NamedTuple):
    """Detailed order information."""
    order_id: str
    client_id: Optional[str]
    symbol: str
    side: str  # BUY or SELL
    order_type: str  # LIMIT or MARKET
    qty: float  # Order quantity
    price: Optional[float]  # Order price (None for market orders)
    filled_qty: float  # Filled quantity
    remaining_qty: float  # Remaining quantity
    status: str  # Order status
    avg_price: Optional[float]  # Average fill price
    fee: Optional[float]  # Trading fee
    fee_coin: Optional[str]  # Fee currency
    create_time: Optional[int] = None  # Order creation timestamp
    update_time: Optional[int] = None  # Last update timestamp
    # Take Profit/Stop Loss info
    tp_price: Optional[float] = None
    tp_order_type: Optional[str] = None
    sl_price: Optional[float] = None
    sl_order_type: Optional[str] = None


class CancelOrderRequest(NamedTuple):
    """Request parameters for cancelling orders."""
    symbol: str
    order_list: list  # List of dicts with orderId and/or clientId


class CancelOrderResponse(NamedTuple):
    """Response from order cancellation."""
    success_list: list  # List of successfully cancelled orders
    failure_list: list  # List of failed cancellations with error info


class ModifyOrderRequest(NamedTuple):
    """Request parameters for modifying an order."""
    order_id: Optional[str] = None
    client_id: Optional[str] = None
    qty: Optional[str] = None
    price: Optional[str] = None
    # Take Profit parameters
    tp_price: Optional[str] = None
    tp_stop_type: Optional[str] = None
    tp_order_type: Optional[str] = None
    tp_order_price: Optional[str] = None
    # Stop Loss parameters
    sl_price: Optional[str] = None
    sl_stop_type: Optional[str] = None
    sl_order_type: Optional[str] = None
    sl_order_price: Optional[str] = None
