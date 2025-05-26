import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class OandaConfig:
    """OANDA API configuration"""
    api_key: str
    api_url: str
    account_id: str
    environment: str = "practice"  # 'practice' or 'live'
    
    @classmethod
    def from_env(cls) -> 'OandaConfig':
        """Create OandaConfig from environment variables"""
        api_key = os.getenv('OANDA_DEMO_KEY')
        api_url = os.getenv('OANDA_DEMO_URL')
        account_id = os.getenv('OANDA_DEMO_ACCOUNT_ID')
        
        if not all([api_key, api_url, account_id]):
            raise ValueError(
                "Missing OANDA credentials in environment variables. "
                "Please set OANDA_DEMO_KEY, OANDA_DEMO_URL, and OANDA_DEMO_ACCOUNT_ID"
            )
        
        logger.info("Loaded OANDA credentials from environment variables")
        return cls(
            api_key=api_key,
            api_url=api_url,
            account_id=account_id
        )

# Create global config instance
oanda_config = OandaConfig.from_env() 