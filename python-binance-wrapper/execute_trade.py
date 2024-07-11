import ccxt
from dotenv import load_dotenv
import os
import requests
import socket
from requests_toolbelt.adapters.socket_options import SocketOptionsAdapter

# Load environment variables from .env file
load_dotenv()

# Fetch API keys from environment variables
API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_API_SECRET')

# Setup logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def create_market_buy_order(symbol, amount):
    try:
        # Initialize the exchange with IPv4 setting
        exchange = ccxt.binanceus({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
        })

        # Assign the modified session back to the exchange
        exchange.session = session

        # Print the exchange markets to ensure it's working
        print("Fetching exchange markets...")
        markets = exchange.load_markets()
        print("Markets loaded successfully")

        # Create a market buy order
        order = exchange.create_market_buy_order(symbol, amount)
        
        # Print the order details
        print(order)
        
    except ccxt.NetworkError as e:
        print(f"A network error occurred: {e}")
    except ccxt.ExchangeError as e:
        print(f"An exchange error occurred: {e}")
    except ccxt.BaseError as e:
        print(f"A general error occurred: {e}")

if __name__ == "__main__":
    # Define the trading pair and amount to buy
    symbol = 'BTCUSDT'
    amount = 0.0001  # Adjust the amount as needed
    
    # Execute the market buy order
    create_market_buy_order(symbol, amount)
