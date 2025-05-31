import os

class Config:
    def __init__(self):
        self.oanda_api_key = os.getenv('OANDA_API_KEY', 'your_oanda_api_key_here')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID', 'your_oanda_account_id')
        self.oanda_environment = os.getenv('OANDA_ENVIRONMENT', 'practice')  # 'live' or 'practice'

config = Config()
