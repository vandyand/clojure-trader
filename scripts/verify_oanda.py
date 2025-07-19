#!/usr/bin/env python3
import sys
import os
import argparse
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify_oanda")

try:
    from oandapyV20 import API
    from oandapyV20.endpoints.accounts import AccountDetails
    OANDA_AVAILABLE = True
except ImportError:
    logger.error("oandapyV20 not installed. Run: pip install oandapyV20")
    OANDA_AVAILABLE = False
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Verify OANDA API connection")
    
    parser.add_argument("--account-id", type=str, help="OANDA account ID (overrides env var)")
    parser.add_argument("--api-token", type=str, help="OANDA API token (overrides env var)")
    parser.add_argument("--practice", action="store_true", default=True,
                       help="Use practice environment (default: True)")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Get credentials
    account_id = args.account_id or os.environ.get('OANDA_DEMO_ACCOUNT_ID')
    api_token = args.api_token or os.environ.get('OANDA_DEMO_KEY')
    environment = "practice" if args.practice else "live"
    
    if not account_id:
        logger.error("No account ID provided. Please set OANDA_DEMO_ACCOUNT_ID environment variable or use --account-id")
        return 1
    
    if not api_token:
        logger.error("No API token provided. Please set OANDA_DEMO_KEY environment variable or use --api-token")
        return 1
    
    logger.info(f"Attempting to connect to OANDA {environment} API")
    logger.info(f"Account ID: {account_id}")
    logger.info(f"API Token: {api_token[:10]}...")
    
    try:
        api = API(access_token=api_token, environment=environment)
        request = AccountDetails(accountID=account_id)
        response = api.request(request)
        
        logger.info(f"Successfully connected to OANDA {environment} API")
        logger.info(f"Account name: {response.get('account', {}).get('alias')}")
        logger.info(f"Account currency: {response.get('account', {}).get('currency')}")
        logger.info(f"Account balance: {response.get('account', {}).get('balance')}")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to connect to OANDA API: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 