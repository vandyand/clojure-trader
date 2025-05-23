"""
Bitunix API integration package.
"""
from .client import BitUnixClient
from .models import Candlestick, AccountBalance, PositionInfo, AccountSummary
from .auth import BitunixAuth

__all__ = [
    'BitUnixClient',
    'Candlestick',
    'AccountBalance',
    'PositionInfo',
    'AccountSummary',
    'BitunixAuth'
]

__version__ = '0.1.0' 