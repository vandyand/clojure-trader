import robin_stocks.robinhood as rh
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

RH_USERNAME = os.getenv('ROBINHOOD_USERNAME')
RH_PASSWORD = os.getenv('ROBINHOOD_PASSWORD')

# Login to Robinhood
rh.login(RH_USERNAME, RH_PASSWORD)

def post_market_order(symbol, amount):
    try:
        if amount > 0:
            order = rh.orders.order_buy_fractional_by_price(symbol, amount)
        elif amount == 0:
            order = None
        else:
            order = rh.orders.order_sell_fractional_by_price(symbol, abs(amount))
        print(order)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    symbol = 'NVDA'
    amount = -1.00  # Adjust the amount as needed
    post_market_order(symbol, amount)
