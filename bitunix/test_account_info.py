from client import BitUnixClient, AccountBalance, PositionInfo
from typing import List

# This is an integration test script. 
# It REQUIRES valid BITUNIX_API_KEY and BITUNIX_SECRET_KEY to be set in environment variables
# or in a .env file in the root of the workspace.

def main():
    print("Attempting to initialize BitUnixClient for private endpoints...")
    try:
        client = BitUnixClient()
        if client.public_only:
            print("ERROR: API Key and/or Secret Key are missing. Cannot test private endpoints.")
            return
        print("BitUnixClient initialized successfully for private endpoint testing.")
    except Exception as e:
        print(f"Error initializing BitUnixClient: {e}")
        return

    # --- Test Get Account Balance ---
    margin_coin_to_test = "USDT" # Change if you use a different margin coin
    print(f"\nFetching account balance for margin coin: {margin_coin_to_test}...")
    try:
        balances: List[AccountBalance] = client.get_account_balance(margin_coin=margin_coin_to_test)
        if balances:
            print(f"Successfully fetched {len(balances)} account balance entry/entries:")
            for b in balances:
                print(
                    f"  Coin: {b.margin_coin}, Available: {b.available}, Frozen: {b.frozen}, Margin: {b.margin}, "
                    f"Transferable: {b.transfer}, Mode: {b.position_mode}, Cross PNL: {b.cross_unrealized_pnl}, "
                    f"Isolation PNL: {b.isolation_unrealized_pnl}, Bonus: {b.bonus}"
                )
        else:
            print(f"No balance information returned for {margin_coin_to_test}, or an empty list was received.")
    except Exception as e:
        print(f"Error fetching account balance: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")

    # --- Test Get Open Positions (All) ---
    print("\nFetching all open positions...")
    try:
        positions_all: List[PositionInfo] = client.get_open_positions()
        if positions_all:
            print(f"Successfully fetched {len(positions_all)} open position(s):")
            for p in positions_all:
                print(
                    f"  Symbol: {p.symbol}, Side: {p.position_side}, Entry: {p.entry_price}, Amt: {p.position_amt}, "
                    f"Leverage: {p.leverage}, Margin Type: {p.margin_type}, PNL: {p.unrealized_pnl}, ID: {p.position_id}"
                )
        else:
            print("No open positions found, or an empty list was received.")
    except Exception as e:
        print(f"Error fetching all open positions: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")

    # --- Test Get Open Positions (Specific Symbol) ---
    # Note: You might not have an open position for BTCUSDT. This is just for testing the call.
    specific_symbol = "BTCUSDT"
    print(f"\nFetching open positions for symbol: {specific_symbol}...")
    try:
        positions_symbol: List[PositionInfo] = client.get_open_positions(symbol=specific_symbol)
        if positions_symbol:
            print(f"Successfully fetched {len(positions_symbol)} open position(s) for {specific_symbol}:")
            for p in positions_symbol:
                print(
                    f"  Symbol: {p.symbol}, Side: {p.position_side}, Entry: {p.entry_price}, Amt: {p.position_amt}, "
                    f"Leverage: {p.leverage}, Margin Type: {p.margin_type}, PNL: {p.unrealized_pnl}, ID: {p.position_id}"
                )
        else:
            print(f"No open positions found for {specific_symbol}, or an empty list was received.")
    except Exception as e:
        print(f"Error fetching open positions for {specific_symbol}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    main() 