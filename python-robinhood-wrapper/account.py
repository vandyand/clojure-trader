import robin_stocks.robinhood as rh
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

RH_USERNAME = os.getenv('ROBINHOOD_USERNAME')
RH_PASSWORD = os.getenv('ROBINHOOD_PASSWORD')

# Login to Robinhood
rh.login(RH_USERNAME, RH_PASSWORD)

def get_account():
    portfolio = None
    try:
        # profile = rh.account.load_account_profile()
        # print(profile, "\n\n")
        portfolio = rh.profiles.load_portfolio_profile(account_number='5UD97585')
        print(portfolio, "\n\n")
    except Exception as e:
        print(e)

    return portfolio

if __name__ == "__main__":
    account = get_account()
    print(account)