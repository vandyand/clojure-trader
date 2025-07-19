"""
Market data endpoints for Bitunix API.
"""
from typing import List, Optional
from ..models import Candlestick
from datetime import datetime


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
        limit: Optional[int] = 200,        # Default 100, max 200
        kline_type: Optional[str] = "LAST_PRICE"   # 'LAST_PRICE' or 'MARK_PRICE'
    ) -> List[Candlestick]:
        """
        Fetch historical kline (candlestick) data from Bitunix futures endpoint.
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Time interval (e.g., '1d')
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
            "limit": limit,
            "type": kline_type
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        raw_klines = self.client._request("GET", endpoint, params=params, is_private=False)
        candlesticks = []
        if raw_klines:
            for k in raw_klines:
                candlesticks.append(
                    Candlestick(
                        open_time=int(k["time"]),
                        open_price=float(k["open"]),
                        high_price=float(k["high"]),
                        low_price=float(k["low"]),
                        close_price=float(k["close"]),
                        volume=float(k["baseVol"]),
                        quote_volume=float(k["quoteVol"]),
                        kline_type=k.get("type", kline_type)
                    )
                )
        return candlesticks

    def get_spot_historical_klines(
        self,
        symbol: str,
        interval: str = "1",  # Default to 1 minute
        end_time: Optional[int] = None,
        limit: int = 200
    ) -> List[Candlestick]:
        """
        Fetch historical kline (candlestick) data from Bitunix spot endpoint.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Time interval (1,3,5,15,30,60,120,240,360,720,D,M,W)
            end_time: End timestamp in seconds (optional)
            limit: Number of klines to fetch (1-500, default 200)
            
        Returns:
            List of Candlestick objects
        """
        endpoint = "/api/spot/v1/market/kline/history"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 500)  # Ensure limit doesn't exceed 500
        }
        if end_time is not None:
            params["endTime"] = end_time
            
        raw_klines = self.client._request("GET", endpoint, params=params, is_private=False)
        candlesticks = []
        if raw_klines and isinstance(raw_klines, list):
            for k in raw_klines:
                # Convert ISO8601 timestamp to milliseconds
                ts = int(datetime.fromisoformat(k["ts"].replace("Z", "+00:00")).timestamp() * 1000)
                candlesticks.append(
                    Candlestick(
                        open_time=ts,
                        open_price=float(k["open"]),
                        high_price=float(k["high"]),
                        low_price=float(k["low"]),
                        close_price=float(k["close"]),
                        volume=float(k["volume"]),
                        quote_volume=float(k.get("quoteVolume", 0.0)),
                        kline_type="LAST_PRICE"  # Spot API doesn't provide kline type
                    )
                )
        return candlesticks
