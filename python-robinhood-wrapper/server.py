from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import robin_stocks.robinhood as rh

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

RH_USERNAME = os.getenv('ROBINHOOD_USERNAME')
RH_PASSWORD = os.getenv('ROBINHOOD_PASSWORD')

# Login to Robinhood
login = rh.login(RH_USERNAME, RH_PASSWORD)

@app.route('/candlestick', methods=['GET'])
def get_candlestick():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Missing 'symbol' parameter (string)"}), 400

    interval = request.args.get('timeframe')
    if not interval:
        return jsonify({"error": "Missing 'timeframe' parameter (string)"}), 400
    
    span = request.args.get('span')
    if not span:
        return jsonify({"error": "Missing 'span' parameter (string)"}), 400

    try:
        data = rh.stocks.get_stock_historicals(symbol, interval, span)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(data)

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

@app.route('/order', methods=['POST'])
def create_order():
    data = request.json
    symbol = data.get('symbol')
    amount = data.get('amount')

    if not symbol or not isinstance(symbol, str):
        return jsonify({"error": "Invalid or missing 'symbol' parameter (string)"}), 400

    if amount is None or not isinstance(amount, (int, float)):
        return jsonify({"error": "Invalid or missing 'amount' parameter (int or float)"}), 400

    order = post_market_order(symbol, amount)

    return jsonify(order)

@app.route('/balances', methods=['GET'])
def get_balances():
    try:
        balances = []
        positions = rh.account.get_all_positions()

        for position in positions:
            if position['quantity'] != "0.00000000":
                balances.append({
                    'instrument': position['symbol'],
                    'units': float(position['quantity'])
                })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(balances)

@app.route('/portfolio_profile', methods=['GET'])
def get_portfolio_profile():
    portfolio = None
    try:
        # profile = rh.account.load_account_profile()
        # print(profile, "\n\n")
        portfolio_blob = rh.profiles.load_portfolio_profile(account_number='5UD97585')
        portfolio = {
            'equity': portfolio_blob['equity'],
            'extended_hours_equity': portfolio_blob['extended_hours_equity']
        }

    except Exception as e:
        print(e)

    return jsonify(portfolio)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4322)