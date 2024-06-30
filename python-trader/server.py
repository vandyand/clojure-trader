from flask import Flask, request, jsonify
import ccxt
import pandas as pd

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(port=5000)
