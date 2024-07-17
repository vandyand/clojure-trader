import robin_stocks.robinhood as rh
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

RH_USERNAME = os.getenv('ROBINHOOD_USERNAME')
RH_PASSWORD = os.getenv('ROBINHOOD_PASSWORD')

# Login to Robinhood
rh.login(RH_USERNAME, RH_PASSWORD)

def get_free_balances():
    profile = rh.profiles.load_account_profile()
    balances = {
        'cash': profile['cash'],
        'buying_power': profile['buying_power']
    }
    return balances

if __name__ == "__main__":
    balances = get_free_balances()
    print(balances)