import requests

# Make API request
response = requests.get('https://api.binance.us/api/v3/exchangeInfo')
data = response.json()

# Extract symbols
symbols = [item['symbol'] for item in data['symbols'] if item['status'] == 'TRADING']

print(f"Number of tradable symbols: {len(symbols)}")
print(symbols)
