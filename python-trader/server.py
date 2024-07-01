from flask import Flask, request, jsonify
import ccxt
import pandas as pd
from dotenv import load_dotenv
import os
import requests
import socket

# Import the get_free_balances function from fetch_balance.py
from fetch_balance import get_free_balances

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_API_SECRET')

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

session = requests.Session()
session.mount('http://', IPv4Adapter())
session.mount('https://', IPv4Adapter())

def fetch_candlestick_data(symbol, timeframe, since=None, limit=100):
    exchange = ccxt.binanceus()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.to_dict(orient='records')

@app.route('/candlestick', methods=['GET'])
def get_candlestick():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Missing 'symbol' parameter"}), 400

    timeframe = request.args.get('timeframe', '1h')
    limit = int(request.args.get('limit', 100))
    
    since_str = request.args.get('since')
    since = None
    if since_str:
        since = pd.to_datetime(since_str).timestamp() * 1000  # Convert to milliseconds

    try:
        data = fetch_candlestick_data(symbol, timeframe, since, limit)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(data)

@app.route('/order', methods=['POST'])
def create_order():
    data = request.json
    symbol = data.get('symbol')
    order_type = data.get('type')  # 'market', 'limit'
    side = data.get('side')  # 'buy', 'sell'
    amount = data.get('amount')
    price = data.get('price') if order_type == 'limit' else None

    if not all([symbol, order_type, side, amount]):
        return jsonify({"error": "Missing required parameters"}), 400

    exchange = ccxt.binanceus({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
    })
    exchange.session = session

    try:
        if order_type == 'market':
            if side == 'buy':
                order = exchange.create_market_buy_order(symbol, amount)
            else:
                order = exchange.create_market_sell_order(symbol, amount)
        elif order_type == 'limit':
            if side == 'buy':
                order = exchange.create_limit_buy_order(symbol, amount, price)
            else:
                order = exchange.create_limit_sell_order(symbol, amount, price)
        else:
            return jsonify({"error": "Invalid order type"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(order)

@app.route('/balances', methods=['GET'])
def get_balances():
    try:
        free_balances = get_free_balances()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(free_balances)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4321)