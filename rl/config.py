import os
import json

# Load sensitive keys from .sensitive.json if present
SENSITIVE_PATH = os.path.join(os.path.dirname(__file__), '..', '.sensitive.json')
if os.path.exists(SENSITIVE_PATH):
    with open(SENSITIVE_PATH) as f:
        secrets = json.load(f)
else:
    secrets = {}

# Database config
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'rl_forex')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

# OANDA API config
# Use demo key for development
OANDA_API_KEY = secrets.get('OANDA_DEMO_KEY', os.getenv('OANDA_API_KEY', 'YOUR_OANDA_API_KEY'))
OANDA_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID', 'YOUR_OANDA_ACCOUNT_ID')
OANDA_API_URL = os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com/v3') 