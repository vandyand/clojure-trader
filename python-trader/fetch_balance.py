import ccxt
from dotenv import load_dotenv
import os
import requests
import socket
import json

# Load environment variables from .env file
load_dotenv()

# Fetch API keys from environment variables
API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_API_SECRET')

# Custom adapter to force IPv4
class IPv4Adapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        # Force IPv4
        kwargs['socket_options'] = [
            (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
            (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
            (socket.IPPROTO_IP, socket.IPV6_V6ONLY, 0)
        ]
        super(IPv4Adapter, self).init_poolmanager(*args, **kwargs)
    
    def proxy_manager_for(self, *args, **kwargs):
        # Force IPv4 for proxies
        kwargs['socket_options'] = [
            (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
            (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
            (socket.IPPROTO_IP, socket.IPV6_V6ONLY, 0)
        ]
        return super(IPv4Adapter, self).proxy_manager_for(*args, **kwargs)

# Initialize session and mount adapter
session = requests.Session()
session.mount('http://', IPv4Adapter())
session.mount('https://', IPv4Adapter())

# Fetch account balance
def fetch_account_balance():
    try:
        exchange = ccxt.binanceus({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
        })
        exchange.session = session
        balance = exchange.fetch_balance()
        return balance
    except ccxt.BaseError as e:
        print(f"An error occurred: {e}")

def parse_balance(balance):
    free_balances = {}
    
    for asset in balance['info']['balances']:
        free_balances[asset['asset']] = float(asset['free'])  # Convert to float
    
    return free_balances

def get_free_balances():
    account_balance = fetch_account_balance()
    free_balances = parse_balance(account_balance)
    return free_balances

if __name__ == "__main__":
    account_balance = fetch_account_balance()
    
    with open('account_balance.txt', 'w') as file:
        file.write(str(account_balance))
    
    print(account_balance)
    
    # Parse the balance to get only the "free" values
    free_balances = parse_balance(account_balance)
    
    with open('free_balances.txt', 'w') as file:
        file.write(json.dumps(free_balances, indent=4))
    
    print(free_balances)