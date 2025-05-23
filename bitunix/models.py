"""
Data models for Bitunix API integration.
"""
from typing import NamedTuple, Optional


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
