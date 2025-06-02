import oandapyV20
from oandapyV20 import API
from oandapyV20.endpoints import instruments
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import List, Dict
from config.settings import config

logger = logging.getLogger(__name__)

class OandaDataClient:
    """OANDA API client for fetching forex data"""

    def __init__(self, api_key: str = None, account_id: str = None, environment: str = None):
        self.api_key = api_key or config.oanda_api_key
        self.account_id = account_id or config.oanda_account_id
        self.environment = environment or config.oanda_environment

        if not self.api_key:
            raise ValueError("OANDA API key is required")

        self.api = API(access_token=self.api_key, environment=self.environment)
        self.rate_limit_delay = 0.1  # 100ms between requests

    def fetch_historical_data(self,
                            instrument: str,
                            granularity: str = "D",
                            count: int = 5000,
                            to: datetime = None) -> pd.DataFrame:
        """
        Fetch historical candlestick data for an instrument

        Args:
            instrument: Forex pair (e.g., "EUR_USD")
            granularity: Timeframe ("D" for daily)
            count: Number of candles to fetch
            to: Optional time to fetch candles before

        Returns:
            DataFrame with OHLCV data
        """
        try:
            params = {
                "granularity": granularity,
                "count": count
            }
            if to:
                params["to"] = to.isoformat() + 'Z'
                
            request = instruments.InstrumentsCandles(
                instrument=instrument,
                params=params
            )

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            response = self.api.request(request)
            candles = response.get('candles', [])

            if not candles:
                logger.warning(f"No candles returned for {instrument}")
                return pd.DataFrame()

            # Convert to DataFrame
            data = []
            for candle in candles:
                if candle['complete']:
                    data.append({
                        'time': pd.to_datetime(candle['time']),
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': int(candle['volume'])
                    })

            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('time', inplace=True)
                df.sort_index(inplace=True)

            logger.info(f"Fetched {len(df)} candles for {instrument}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {instrument}: {e}")
            return pd.DataFrame()

    def fetch_recent_data(self, instrument: str, days=10) -> pd.DataFrame:
        """
        Fetch the most recent candles for an instrument
        """
        end_time = datetime.utcnow()
        return self.fetch_historical_data(instrument, "D", days, end_time)

    def fetch_multiple_instruments(self,
                                 instruments: List[str],
                                 granularity: str = "D",
                                 count: int = 5000) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple instruments

        Args:
            instruments: List of forex pairs
            granularity: Timeframe
            count: Number of candles per instrument

        Returns:
            Dictionary mapping instrument to DataFrame
        """
        data = {}

        for instrument in instruments:
            logger.info(f"Fetching data for {instrument}")
            df = self.fetch_historical_data(instrument, granularity, count)

            if not df.empty:
                data[instrument] = df
            else:
                logger.warning(f"No data retrieved for {instrument}")

        return data
