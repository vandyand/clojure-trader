import os
import finnhub
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Finnhub client
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

def get_finnhub_symbols():
    try:
        # Fetch stock symbols
        symbols = finnhub_client.stock_symbols('US')
        
        # Extract symbol and description
        symbol_list = [{'symbol': symbol['symbol'], 'description': symbol['description']} for symbol in symbols]
        
        return symbol_list
    except Exception as e:
        print(f"Error fetching symbols from Finnhub: {str(e)}")
        return []

if __name__ == '__main__':
    symbols = get_finnhub_symbols()
    
    if symbols:
        print("Supported symbols:")
        for symbol in symbols:
            print(f"{symbol['symbol']}: {symbol['description']}")
    else:
        print("No symbols found or an error occurred.")