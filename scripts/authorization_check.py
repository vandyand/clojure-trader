#!/usr/bin/env python3
"""
Validate OANDA API authorization
"""

import os
import logging
from config.settings import config
from oandapyV20 import API
from oandapyV20.endpoints.accounts import AccountDetails

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_authorization():
    try:
        api = API(config.oanda_api_key, environment=config.oanda_environment)
        request = AccountDetails(config.oanda_account_id)
        
        try:
            response = api.request(request)
            logger.info("Authorization successful! API response:")
            logger.info(response)
            return True
        except Exception as e:
            logger.error(f"Authorization failed: {str(e)}")
            if 'client' in dir(e) and 'status' in dir(e):
                logger.error(f"HTTP status: {e.status}")
                logger.error(f"Response body: {e.body}")
            return False
    except Exception as e:
        logger.exception("Authorization check failed:")
        return False

if __name__ == "__main__":
    result = check_authorization()
    logger.info(f"Authorization check result: {'SUCCESS' if result else 'FAILURE'}")
