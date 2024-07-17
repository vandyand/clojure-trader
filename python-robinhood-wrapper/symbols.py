import robin_stocks.robinhood as rh
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

RH_USERNAME = os.getenv('ROBINHOOD_USERNAME')
RH_PASSWORD = os.getenv('ROBINHOOD_PASSWORD')

# Login to Robinhood
rh.login(RH_USERNAME, RH_PASSWORD)

def get_tradable_symbols():
    try:
        symbols = rh.stocks.get_all_instruments()
        tradable_symbols = [symbol['symbol'] for symbol in symbols if symbol['tradability'] == 'tradable']
        return tradable_symbols
    except Exception as e:
        print(f"Error fetching symbols from Robinhood: {str(e)}")
        return []

if __name__ == '__main__':
    symbols = get_tradable_symbols()
    if symbols:
        print("Supported symbols:")
        for symbol in symbols:
            print(symbol)
    else:
        print("No symbols found or an error occurred.")