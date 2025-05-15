#!/usr/bin/env python3
import os
import sys
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("list_accounts")

try:
    from oandapyV20 import API
    from oandapyV20.endpoints.accounts import AccountList
except ImportError:
    logger.error("oandapyV20 not installed. Run: pip install oandapyV20")
    sys.exit(1)

def main():
    # Get API token from environment variable
    api_token = os.environ.get('OANDA_DEMO_KEY')
    
    if not api_token:
        logger.error("No API token provided. Please set OANDA_DEMO_KEY environment variable.")
        return 1
    
    logger.info(f"Using API token: {api_token[:10]}...")
    
    try:
        # Connect to OANDA API
        api = API(access_token=api_token, environment="practice")
        
        # Request list of accounts
        request = AccountList()
        response = api.request(request)
        
        if 'accounts' in response and response['accounts']:
            logger.info("Found accounts:")
            for account in response['accounts']:
                logger.info(f"  Account ID: {account['id']}")
                if 'tags' in account:
                    logger.info(f"  Tags: {account['tags']}")
                logger.info("---")
            return 0
        else:
            logger.error("No accounts found or unexpected response format.")
            logger.info(f"Response: {response}")
            return 1
    except Exception as e:
        logger.error(f"Error accessing OANDA API: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 