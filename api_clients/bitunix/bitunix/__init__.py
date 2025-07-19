"""
Bitunix API integration package.
"""
from .client import BitUnixClient
from .models import (
    Candlestick, AccountBalance, PositionInfo, AccountSummary,
    OrderRequest, OrderResponse, OrderInfo, CancelOrderRequest, 
    CancelOrderResponse, ModifyOrderRequest,
    OrderSide, TradeSide, OrderType, OrderStatus, TimeInForce, StopType
)
from .auth import BitunixAuth

__all__ = [
    'BitUnixClient',
    'Candlestick',
    'AccountBalance',
    'PositionInfo',
    'AccountSummary',
    'OrderRequest',
    'OrderResponse',
    'OrderInfo',
    'CancelOrderRequest',
    'CancelOrderResponse',
    'ModifyOrderRequest',
    'OrderSide',
    'TradeSide',
    'OrderType',
    'OrderStatus',
    'TimeInForce',
    'StopType',
    'BitunixAuth'
]

__version__ = '0.1.0' 