"""
Order endpoints for Bitunix API.
"""
from typing import List, Optional, Dict, Any
from ..models import (
    OrderRequest, OrderResponse, OrderInfo, CancelOrderRequest, 
    CancelOrderResponse, ModifyOrderRequest
)
from ..auth import DEBUG_SIGNATURE
import time
import uuid


class OrderEndpoints:
    """Handles order-related endpoints."""
    
    def __init__(self, client):
        self.client = client
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        order_type: str,  # "LIMIT" or "MARKET"
        qty: str,
        price: Optional[str] = None,
        trade_side: Optional[str] = None,  # "OPEN" or "CLOSE" (hedge mode)
        position_id: Optional[str] = None,
        effect: str = "GTC",  # Time in force
        client_id: Optional[str] = None,
        reduce_only: bool = False,
        # Take Profit parameters
        tp_price: Optional[str] = None,
        tp_stop_type: Optional[str] = None,
        tp_order_type: Optional[str] = None,
        tp_order_price: Optional[str] = None,
        # Stop Loss parameters
        sl_price: Optional[str] = None,
        sl_stop_type: Optional[str] = None,
        sl_order_type: Optional[str] = None,
        sl_order_price: Optional[str] = None
    ) -> OrderResponse:
        """
        Place a new order.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: Order direction ("BUY" or "SELL")
            order_type: Order type ("LIMIT" or "MARKET")
            qty: Order quantity as string
            price: Order price (required for LIMIT orders)
            trade_side: Trade side for hedge mode ("OPEN" or "CLOSE")
            position_id: Position ID (required when closing position)
            effect: Time in force ("GTC", "IOC", "FOK", "POST_ONLY")
            client_id: Custom order ID
            reduce_only: Whether to only reduce position
            tp_price: Take profit trigger price
            tp_stop_type: Take profit trigger type ("MARK_PRICE" or "LAST_PRICE")
            tp_order_type: Take profit order type ("LIMIT" or "MARKET")
            tp_order_price: Take profit order price
            sl_price: Stop loss trigger price
            sl_stop_type: Stop loss trigger type ("MARK_PRICE" or "LAST_PRICE")
            sl_order_type: Stop loss order type ("LIMIT" or "MARKET")
            sl_order_price: Stop loss order price
        
        Returns:
            OrderResponse with order_id and client_id
        """
        if self.client.public_only:
            raise ValueError("Cannot place order without API key and secret.")
        
        # Validate required parameters
        if order_type == "LIMIT" and price is None:
            raise ValueError("Price is required for LIMIT orders.")
        
        # Generate client_id if not provided
        if client_id is None:
            client_id = f"py_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        endpoint = "/api/v1/futures/trade/place_order"
        
        # Build request data
        data = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "effect": effect,
            "clientId": client_id,
            "reduceOnly": reduce_only
        }
        
        # Add price for LIMIT orders
        if price is not None:
            data["price"] = price
        
        # Add trade side for hedge mode
        if trade_side is not None:
            data["tradeSide"] = trade_side
        
        # Add position ID for closing positions
        if position_id is not None:
            data["positionId"] = position_id
        
        # Add Take Profit parameters
        if tp_price is not None:
            data["tpPrice"] = tp_price
            if tp_stop_type:
                data["tpStopType"] = tp_stop_type
            if tp_order_type:
                data["tpOrderType"] = tp_order_type
            if tp_order_price:
                data["tpOrderPrice"] = tp_order_price
        
        # Add Stop Loss parameters
        if sl_price is not None:
            data["slPrice"] = sl_price
            if sl_stop_type:
                data["slStopType"] = sl_stop_type
            if sl_order_type:
                data["slOrderType"] = sl_order_type
            if sl_order_price:
                data["slOrderPrice"] = sl_order_price
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Order] Placing order: {data}")
        
        response = self.client._request("POST", endpoint, data=data, is_private=True)
        
        return OrderResponse(
            order_id=response["orderId"],
            client_id=response.get("clientId")
        )
    
    def cancel_orders(
        self,
        symbol: str,
        order_list: List[Dict[str, str]]
    ) -> CancelOrderResponse:
        """
        Cancel one or more orders.
        
        Args:
            symbol: Trading pair
            order_list: List of orders to cancel, each containing 'orderId' and/or 'clientId'
        
        Returns:
            CancelOrderResponse with success and failure lists
        """
        if self.client.public_only:
            raise ValueError("Cannot cancel orders without API key and secret.")
        
        endpoint = "/api/v1/futures/trade/cancel_orders"
        
        data = {
            "symbol": symbol,
            "orderList": order_list
        }
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Order] Cancelling orders: {data}")
        
        response = self.client._request("POST", endpoint, data=data, is_private=True)
        
        return CancelOrderResponse(
            success_list=response.get("successList", []),
            failure_list=response.get("failureList", [])
        )
    
    def cancel_order(self, symbol: str, order_id: Optional[str] = None, client_id: Optional[str] = None) -> CancelOrderResponse:
        """
        Cancel a single order by order_id or client_id.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
            client_id: Client ID to cancel
        
        Returns:
            CancelOrderResponse
        """
        if not order_id and not client_id:
            raise ValueError("Either order_id or client_id must be provided.")
        
        order_info = {}
        if order_id:
            order_info["orderId"] = order_id
        if client_id:
            order_info["clientId"] = client_id
        
        return self.cancel_orders(symbol, [order_info])
    
    def modify_order(
        self,
        order_id: Optional[str] = None,
        client_id: Optional[str] = None,
        qty: Optional[str] = None,
        price: Optional[str] = None,
        # Take Profit parameters
        tp_price: Optional[str] = None,
        tp_stop_type: Optional[str] = None,
        tp_order_type: Optional[str] = None,
        tp_order_price: Optional[str] = None,
        # Stop Loss parameters
        sl_price: Optional[str] = None,
        sl_stop_type: Optional[str] = None,
        sl_order_type: Optional[str] = None,
        sl_order_price: Optional[str] = None
    ) -> OrderResponse:
        """
        Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            client_id: Client ID to modify
            qty: New quantity
            price: New price
            tp_price: New take profit price
            tp_stop_type: Take profit trigger type
            tp_order_type: Take profit order type
            tp_order_price: Take profit order price
            sl_price: New stop loss price
            sl_stop_type: Stop loss trigger type
            sl_order_type: Stop loss order type
            sl_order_price: Stop loss order price
        
        Returns:
            OrderResponse with order_id and client_id
        """
        if self.client.public_only:
            raise ValueError("Cannot modify order without API key and secret.")
        
        if not order_id and not client_id:
            raise ValueError("Either order_id or client_id must be provided.")
        
        endpoint = "/api/v1/futures/trade/modify_order"
        
        data = {}
        
        # Add order identification
        if order_id:
            data["orderId"] = order_id
        if client_id:
            data["clientId"] = client_id
        
        # Add order modifications
        if qty is not None:
            data["qty"] = qty
        if price is not None:
            data["price"] = price
        
        # Add Take Profit modifications
        if tp_price is not None:
            data["tpPrice"] = tp_price
        if tp_stop_type is not None:
            data["tpStopType"] = tp_stop_type
        if tp_order_type is not None:
            data["tpOrderType"] = tp_order_type
        if tp_order_price is not None:
            data["tpOrderPrice"] = tp_order_price
        
        # Add Stop Loss modifications
        if sl_price is not None:
            data["slPrice"] = sl_price
        if sl_stop_type is not None:
            data["slStopType"] = sl_stop_type
        if sl_order_type is not None:
            data["slOrderType"] = sl_order_type
        if sl_order_price is not None:
            data["slOrderPrice"] = sl_order_price
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Order] Modifying order: {data}")
        
        response = self.client._request("POST", endpoint, data=data, is_private=True)
        
        return OrderResponse(
            order_id=response["orderId"],
            client_id=response.get("clientId")
        )
    
    def get_pending_orders(self, symbol: Optional[str] = None) -> List[OrderInfo]:
        """
        Get pending/open orders.
        
        Args:
            symbol: Trading pair (optional, if not provided returns all symbols)
        
        Returns:
            List of OrderInfo objects
        """
        if self.client.public_only:
            raise ValueError("Cannot get pending orders without API key and secret.")
        
        endpoint = "/api/v1/futures/trade/get_pending_orders"
        
        data = {}
        if symbol:
            data["symbol"] = symbol
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Order] Getting pending orders for symbol: {symbol}")
        
        response = self.client._request("POST", endpoint, data=data, is_private=True)
        
        orders = []
        if response and isinstance(response, list):
            for order_data in response:
                orders.append(self._parse_order_info(order_data))
        elif response and isinstance(response, dict):
            # Single order returned
            orders.append(self._parse_order_info(response))
        
        return orders
    
    def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[OrderInfo]:
        """
        Get order history.
        
        Args:
            symbol: Trading pair (optional)
            start_time: Start time (timestamp in ms)
            end_time: End time (timestamp in ms)
            page: Page number
            page_size: Items per page
        
        Returns:
            List of OrderInfo objects
        """
        if self.client.public_only:
            raise ValueError("Cannot get order history without API key and secret.")
        
        endpoint = "/api/v1/futures/trade/get_history_orders"
        
        data = {
            "page": page,
            "pageSize": page_size
        }
        
        if symbol:
            data["symbol"] = symbol
        if start_time:
            data["startTime"] = start_time
        if end_time:
            data["endTime"] = end_time
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Order] Getting order history: {data}")
        
        response = self.client._request("POST", endpoint, data=data, is_private=True)
        
        orders = []
        if response and "data" in response and isinstance(response["data"], list):
            for order_data in response["data"]:
                orders.append(self._parse_order_info(order_data))
        elif response and isinstance(response, list):
            for order_data in response:
                orders.append(self._parse_order_info(order_data))
        
        return orders
    
    def get_order_detail(self, order_id: str) -> Optional[OrderInfo]:
        """
        Get detailed information about a specific order.
        
        Args:
            order_id: Order ID to get details for
        
        Returns:
            OrderInfo object or None if not found
        """
        if self.client.public_only:
            raise ValueError("Cannot get order detail without API key and secret.")
        
        endpoint = "/api/v1/futures/trade/get_order_detail"
        
        data = {"orderId": order_id}
        
        if DEBUG_SIGNATURE:
            print(f"[DEBUG Order] Getting order detail for: {order_id}")
        
        try:
            response = self.client._request("POST", endpoint, data=data, is_private=True)
            if response:
                return self._parse_order_info(response)
        except Exception as e:
            if DEBUG_SIGNATURE:
                print(f"[DEBUG Order] Error getting order detail: {e}")
        
        return None
    
    def _parse_order_info(self, order_data: dict) -> OrderInfo:
        """Parse order data from API response into OrderInfo object."""
        return OrderInfo(
            order_id=order_data.get("orderId", ""),
            client_id=order_data.get("clientId"),
            symbol=order_data.get("symbol", ""),
            side=order_data.get("side", ""),
            order_type=order_data.get("orderType", order_data.get("type", "")),
            qty=float(order_data.get("qty", order_data.get("volume", 0))),
            price=float(order_data.get("price", 0)) if order_data.get("price") else None,
            filled_qty=float(order_data.get("filledQty", order_data.get("dealVolume", 0))),
            remaining_qty=float(order_data.get("remainingQty", order_data.get("leftVolume", 0))),
            status=order_data.get("status", ""),
            avg_price=float(order_data.get("avgPrice", 0)) if order_data.get("avgPrice") else None,
            fee=float(order_data.get("fee", 0)) if order_data.get("fee") else None,
            fee_coin=order_data.get("feeCoin"),
            create_time=int(order_data.get("ctime", 0)) if order_data.get("ctime") else None,
            update_time=int(order_data.get("utime", 0)) if order_data.get("utime") else None,
            tp_price=float(order_data.get("tpPrice", 0)) if order_data.get("tpPrice") else None,
            tp_order_type=order_data.get("tpOrderType"),
            sl_price=float(order_data.get("slPrice", 0)) if order_data.get("slPrice") else None,
            sl_order_type=order_data.get("slOrderType")
        ) 