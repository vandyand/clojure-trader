import os

class OandaConfig:
    def __init__(self):
        # Read configuration from environment variables
        self.api_key = os.getenv('OANDA_DEMO_KEY', '')
        self.account_id = os.getenv('OANDA_DEMO_ACCOUNT_ID', '')
        self.environment = os.getenv('OANDA_ENVIRONMENT', 'practice')
        
        # Validate configuration
        if not self.api_key:
            raise ValueError("OANDA API key is not set. Please set OANDA_DEMO_KEY environment variable.")
        if not self.account_id:
            raise ValueError("OANDA Account ID is not set. Please set OANDA_DEMO_ACCOUNT_ID environment variable.")
        if self.environment not in ['practice', 'live']:
            raise ValueError("OANDA_ENVIRONMENT must be either 'practice' or 'live'")

# Global configuration instance
oanda_config = OandaConfig()
