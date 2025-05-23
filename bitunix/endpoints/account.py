"""
Account endpoints for Bitunix API.
"""
from typing import List, Optional
from ..models import AccountBalance, AccountSummary
from ..auth import DEBUG_SIGNATURE


class AccountEndpoints:
    """Handles account-related endpoints."""
    
    def __init__(self, client):
        self.client = client
    
    def get_account_balance(self, margin_coin: str) -> List[AccountBalance]:
        """
        Fetch account balance for a specific margin coin.
        
        Args:
            margin_coin: The margin coin to fetch balance for (e.g., 'USDT')
        
        Returns:
            List of AccountBalance objects
        """
        if self.client.public_only:
            print("Cannot fetch account balance without API key/secret.")
            return []
        
        endpoint = "/api/v1/futures/account"
        params = {"marginCoin": margin_coin}
        
        raw_balances = self.client._request("GET", endpoint, params=params, is_private=True)
        
        balances = []
        if raw_balances:
            # Handle both dict and list responses
            if isinstance(raw_balances, dict):
                # Single balance returned as dict
                if DEBUG_SIGNATURE:
                    print(f"[DEBUG Balance] Received single balance dict")
                balances.append(self._parse_balance(raw_balances))
            elif isinstance(raw_balances, list):
                # Multiple balances returned as list
                if DEBUG_SIGNATURE:
                    print(f"[DEBUG Balance] Received balance list with {len(raw_balances)} items")
                for b_item in raw_balances:
                    if isinstance(b_item, dict):
                        balances.append(self._parse_balance(b_item))
                    else:
                        print(f"[DEBUG Balance] Expected dict item in balance list, got {type(b_item)}: {b_item}")
            else:
                print(f"[DEBUG Balance] Unexpected type for raw_balances: {type(raw_balances)}: {raw_balances}")
        
        return balances
    
    def get_account_summary(self, margin_coins: Optional[List[str]] = None) -> AccountSummary:
        """
        Get comprehensive account summary with total values.
        
        Args:
            margin_coins: List of margin coins to include (default: ['USDT'])
        
        Returns:
            AccountSummary object with total values and individual balances
        """
        if self.client.public_only:
            print("Cannot fetch account summary without API key/secret.")
            return AccountSummary(
                total_balance=0.0,
                total_available=0.0,
                total_frozen=0.0,
                total_margin=0.0,
                total_unrealized_pnl=0.0,
                total_equity=0.0,
                balances=[]
            )
        
        if margin_coins is None:
            margin_coins = ['USDT']  # Default to USDT
        
        all_balances = []
        total_balance = 0.0
        total_available = 0.0
        total_frozen = 0.0
        total_margin = 0.0
        total_unrealized_pnl = 0.0
        
        # Fetch balance for each margin coin
        for coin in margin_coins:
            try:
                balances = self.get_account_balance(margin_coin=coin)
                all_balances.extend(balances)
                
                # Aggregate values
                for balance in balances:
                    # Calculate total balance (available + frozen + margin)
                    coin_balance = balance.available + balance.frozen + balance.margin
                    total_balance += coin_balance
                    total_available += balance.available
                    total_frozen += balance.frozen
                    total_margin += balance.margin
                    
                    # Sum up unrealized PNL
                    total_unrealized_pnl += balance.cross_unrealized_pnl + balance.isolation_unrealized_pnl
                    
            except Exception as e:
                print(f"Error fetching balance for {coin}: {e}")
        
        # Calculate total equity (balance + unrealized PNL)
        total_equity = total_balance + total_unrealized_pnl
        
        return AccountSummary(
            total_balance=total_balance,
            total_available=total_available,
            total_frozen=total_frozen,
            total_margin=total_margin,
            total_unrealized_pnl=total_unrealized_pnl,
            total_equity=total_equity,
            balances=all_balances
        )
    
    def _parse_balance(self, balance_dict: dict) -> AccountBalance:
        """Parse a balance dictionary into an AccountBalance object."""
        return AccountBalance(
            margin_coin=balance_dict["marginCoin"],
            available=float(balance_dict["available"]),
            frozen=float(balance_dict["frozen"]),
            margin=float(balance_dict["margin"]),
            transfer=float(balance_dict["transfer"]),
            position_mode=balance_dict["positionMode"],
            cross_unrealized_pnl=float(balance_dict["crossUnrealizedPNL"]),
            isolation_unrealized_pnl=float(balance_dict["isolationUnrealizedPNL"]),
            bonus=float(balance_dict.get("bonus", 0.0))  # Bonus might not always be present
        )
