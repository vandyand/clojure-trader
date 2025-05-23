"""
Market data endpoints for Bitunix API.
"""
from typing import List, Optional
from ..models import Candlestick


class MarketEndpoints:
    """Handles market data endpoints."""
    
    def __init__(self, client):
        self.client = client
    
    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,  # Unix timestamp in ms
        end_time: Optional[int] = None,    # Unix timestamp in ms
        limit: Optional[int] = None,       # Default 100, max 200
        kline_type: Optional[str] = None   # LAST_PRICE or MARK_PRICE
    ) -> List[Candlestick]:
        """
        Fetch historical kline (candlestick) data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Time interval (e.g., '1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M')
            start_time: Start time in milliseconds (optional)
            end_time: End time in milliseconds (optional)
            limit: Number of klines to fetch (optional, default 100, max 200)
            kline_type: Type of kline (optional, 'LAST_PRICE' or 'MARK_PRICE')
        
        Returns:
            List of Candlestick objects
        """
        endpoint = "/api/v1/futures/market/kline"
        params = {
            "symbol": symbol,
            "interval": interval,
        }
        
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if limit is not None:
            params["limit"] = limit
        if kline_type is not None:
            params["type"] = kline_type
        
        raw_klines = self.client._request("GET", endpoint, params=params, is_private=False)
        
        candlesticks = []
        if raw_klines:  # Ensure raw_klines is not None and is iterable
            for k in raw_klines:
                # Response fields: open, high, low, close, time, quoteVol, baseVol, type
                candlesticks.append(
                    Candlestick(
                        open_time=int(k["time"]),
                        open_price=float(k["open"]),
                        high_price=float(k["high"]),
                        low_price=float(k["low"]),
                        close_price=float(k["close"]),
                        volume=float(k.get("baseVol", 0.0)),  # Use .get for safety
                        quote_volume=float(k.get("quoteVol", 0.0)),
                        kline_type=k.get("type")
                    )
                )
        
        return candlesticks
