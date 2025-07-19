"""
Position endpoints for Bitunix API.
"""
from typing import List, Optional
from ..models import PositionInfo
from ..auth import DEBUG_SIGNATURE


class PositionEndpoints:
    """Handles position-related endpoints."""
    
    def __init__(self, client):
        self.client = client
    
    def get_open_positions(self, symbol: Optional[str] = None, position_id: Optional[str] = None) -> List[PositionInfo]:
        """
        Fetch current open positions.
        
        Args:
            symbol: Trading pair symbol to filter by (optional)
            position_id: Specific position ID to query (optional)
        
        Returns:
            List of PositionInfo objects
        """
        if self.client.public_only:
            print("Cannot fetch open positions without API key/secret.")
            return []
        
        # Correct endpoint based on API documentation
        endpoint = "/api/v1/futures/position/get_pending_positions"
        
        params = {}
        if symbol:
            params["symbol"] = symbol
        if position_id:
            params["positionId"] = position_id
        
        raw_positions = self.client._request("GET", endpoint, params=params if params else None, is_private=True)
        
        positions = []
        if raw_positions:
            # Handle both dict and list responses
            if isinstance(raw_positions, dict):
                # Single position returned as dict
                if DEBUG_SIGNATURE:
                    print(f"[DEBUG Position] Received single position dict")
                positions.append(self._parse_position(raw_positions))
            elif isinstance(raw_positions, list):
                # Multiple positions returned as list
                if DEBUG_SIGNATURE:
                    print(f"[DEBUG Position] Received position list with {len(raw_positions)} items")
                for p_item in raw_positions:
                    if isinstance(p_item, dict):
                        positions.append(self._parse_position(p_item))
                    else:
                        print(f"[DEBUG Position] Expected dict item in position list, got {type(p_item)}: {p_item}")
            else:
                print(f"[DEBUG Position] Unexpected type for raw_positions: {type(raw_positions)}: {raw_positions}")
        
        return positions
    
    def _parse_position(self, position_dict: dict) -> PositionInfo:
        """Parse a position dictionary into a PositionInfo object."""
        # Map Bitunix fields to our PositionInfo structure
        # Bitunix uses different field names than what we originally expected
        return PositionInfo(
            symbol=position_dict["symbol"],
            # Map 'side' to position_side (LONG/SHORT)
            position_side=position_dict["side"],
            unrealized_pnl=float(position_dict.get("unrealizedPNL", 0.0)),
            # Use avgOpenPrice if available, otherwise entryPrice
            entry_price=float(position_dict.get("avgOpenPrice", position_dict.get("entryValue", 0.0))),
            # Use 'qty' field for position amount
            position_amt=float(position_dict.get("qty", 0.0)),
            # Use 'margin' field for initial margin
            initial_margin=float(position_dict.get("margin", 0.0)),
            leverage=int(position_dict.get("leverage", 1)),
            # Map marginMode to margin_type
            margin_type=position_dict.get("marginMode", "").replace("ISOLATION", "ISOLATED"),
            # Additional fields
            position_id=position_dict.get("positionId"),
            qty=float(position_dict.get("qty", 0.0)),
            entry_value=float(position_dict.get("entryValue", 0.0)),
            side=position_dict.get("side"),
            margin_mode=position_dict.get("marginMode"),
            position_mode=position_dict.get("positionMode"),
            fee=float(position_dict.get("fee", 0.0)),
            funding=float(position_dict.get("funding", 0.0)),
            realized_pnl=float(position_dict.get("realizedPNL", 0.0)),
            liq_price=float(position_dict.get("liqPrice", 0.0)),
            margin_rate=float(position_dict.get("marginRate", 0.0)),
            avg_open_price=float(position_dict.get("avgOpenPrice", 0.0)),
            ctime=position_dict.get("ctime"),
            mtime=position_dict.get("mtime")
        )
