#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("position_sizing")

try:
    from oandapyV20 import API
    from oandapyV20.endpoints.pricing import PricingInfo
    OANDA_AVAILABLE = True
except ImportError:
    logger.error("oandapyV20 not installed. Run: pip install oandapyV20")
    OANDA_AVAILABLE = False

# Cache for latest prices to avoid repeated API calls
latest_price_cache = {}

def get_latest_price(instrument, api=None, account_id=None):
    """Get latest price for an instrument, with caching"""
    global latest_price_cache
    
    # Return cached price if available and not too old
    if instrument in latest_price_cache:
        return latest_price_cache[instrument]
    
    # If no API or account_id provided, use environment variables
    if not api:
        api_token = os.environ.get('OANDA_DEMO_KEY')
        if not api_token:
            logger.error("No OANDA API token provided")
            return None
        api = API(access_token=api_token, environment="practice")
    
    if not account_id:
        account_id = os.environ.get('OANDA_DEMO_ACCOUNT_ID')
        if not account_id:
            logger.error("No OANDA account ID provided")
            return None
    
    try:
        params = {"instruments": instrument}
        request = PricingInfo(accountID=account_id, params=params)
        response = api.request(request)
        
        # Extract the mid price (average of bid and ask)
        prices = response.get('prices', [])
        if not prices:
            logger.error(f"No price data returned for {instrument}")
            return None
        
        price_data = prices[0]
        bids = price_data.get('bids', [])
        asks = price_data.get('asks', [])
        
        if not bids or not asks:
            logger.error(f"No bid/ask data for {instrument}")
            return None
        
        bid_price = float(bids[0].get('price'))
        ask_price = float(asks[0].get('price'))
        mid_price = (bid_price + ask_price) / 2.0
        
        # Cache the price
        latest_price_cache[instrument] = mid_price
        
        return mid_price
    except Exception as e:
        logger.error(f"Error getting price for {instrument}: {e}")
        return None

def instrument_ends_in_usd_or_usdt(instrument):
    """Check if instrument ends with USD or USDT"""
    suffix3 = instrument[-3:] if len(instrument) >= 3 else ""
    suffix4 = instrument[-4:] if len(instrument) >= 4 else ""
    return suffix3 == "USD" or suffix4 == "USDT"

def instrument_has_usd_in_it(instrument):
    """Check if instrument contains USD"""
    return "USD" in instrument

def instrument_ends_in_jpy(instrument):
    """Check if instrument ends with JPY"""
    return instrument[-3:] == "JPY" if len(instrument) >= 3 else False

def instrument_ends_in_gbp(instrument):
    """Check if instrument ends with GBP"""
    return instrument[-3:] == "GBP" if len(instrument) >= 3 else False

def instrument_ends_in_nzd(instrument):
    """Check if instrument ends with NZD"""
    return instrument[-3:] == "NZD" if len(instrument) >= 3 else False

def instrument_ends_in_aud(instrument):
    """Check if instrument ends with AUD"""
    return instrument[-3:] == "AUD" if len(instrument) >= 3 else False

def instrument_ends_in_cad(instrument):
    """Check if instrument ends with CAD"""
    return instrument[-3:] == "CAD" if len(instrument) >= 3 else False

def instrument_ends_in_chf(instrument):
    """Check if instrument ends with CHF"""
    return instrument[-3:] == "CHF" if len(instrument) >= 3 else False

def is_crypto(instrument):
    """Check if instrument is a cryptocurrency"""
    return instrument.endswith("USDT")

def is_forex(instrument):
    """Check if instrument is a forex pair"""
    return "_" in instrument and not is_crypto(instrument)

def get_target_position_amount(instrument, latest_price, usd_amount, api=None, account_id=None):
    """
    Calculate target position amount based on instrument type, price, and USD amount.
    This follows the logic in the Clojure code.
    
    Args:
        instrument: The trading instrument (e.g., "EUR_USD", "BTCUSDT")
        latest_price: The current price of the instrument
        usd_amount: The USD amount to allocate to this position
        api: Optional OANDA API client
        account_id: Optional OANDA account ID
        
    Returns:
        The target position size (units)
    """
    try:
        if instrument_ends_in_usd_or_usdt(instrument):
            # For pairs like EUR_USD, GBP_USD, BTCUSDT
            return usd_amount / latest_price
        
        elif instrument_has_usd_in_it(instrument):
            if instrument_ends_in_jpy(instrument):
                # For USD_JPY with JPY as quote currency
                return usd_amount * latest_price * 0.01
            else:
                # For other USD pairs like USD_CAD, USD_CHF
                return usd_amount * latest_price
        
        elif instrument_ends_in_jpy(instrument):
            # For crosses ending in JPY (EUR_JPY, GBP_JPY)
            usd_jpy_price = get_latest_price("USD_JPY", api, account_id)
            if not usd_jpy_price:
                logger.error(f"Could not get USD_JPY price for {instrument} calculation")
                return 0
            return (usd_amount * latest_price) / usd_jpy_price
        
        elif instrument_ends_in_cad(instrument):
            # For crosses ending in CAD (EUR_CAD, GBP_CAD)
            usd_cad_price = get_latest_price("USD_CAD", api, account_id)
            if not usd_cad_price:
                logger.error(f"Could not get USD_CAD price for {instrument} calculation")
                return 0
            return (usd_amount * latest_price) / usd_cad_price
        
        elif instrument_ends_in_chf(instrument):
            # For crosses ending in CHF (EUR_CHF, GBP_CHF)
            usd_chf_price = get_latest_price("USD_CHF", api, account_id)
            if not usd_chf_price:
                logger.error(f"Could not get USD_CHF price for {instrument} calculation")
                return 0
            return (usd_amount * latest_price) / usd_chf_price
        
        elif instrument_ends_in_gbp(instrument):
            # For crosses ending in GBP (EUR_GBP, AUD_GBP)
            gbp_usd_price = get_latest_price("GBP_USD", api, account_id)
            if not gbp_usd_price:
                logger.error(f"Could not get GBP_USD price for {instrument} calculation")
                return 0
            return usd_amount * latest_price * gbp_usd_price
        
        elif instrument_ends_in_nzd(instrument):
            # For crosses ending in NZD (EUR_NZD, GBP_NZD)
            nzd_usd_price = get_latest_price("NZD_USD", api, account_id)
            if not nzd_usd_price:
                logger.error(f"Could not get NZD_USD price for {instrument} calculation")
                return 0
            return usd_amount * latest_price * nzd_usd_price
        
        elif instrument_ends_in_aud(instrument):
            # For crosses ending in AUD (EUR_AUD, GBP_AUD)
            aud_usd_price = get_latest_price("AUD_USD", api, account_id)
            if not aud_usd_price:
                logger.error(f"Could not get AUD_USD price for {instrument} calculation")
                return 0
            return usd_amount * latest_price * aud_usd_price
        
        else:
            # Default case
            return usd_amount / latest_price
    
    except Exception as e:
        logger.error(f"Error calculating position size for {instrument}: {e}")
        return 0

def apply_forex_multiplier(target_positions, multiplier=25):
    """
    Apply a multiplier to forex positions only, as in the Clojure get-balanced-scores function
    
    Args:
        target_positions: List of dicts with position information
        multiplier: Multiplier to apply to forex positions (default: 25)
        
    Returns:
        List of updated position records
    """
    balanced_positions = []
    
    for pos in target_positions:
        instrument = pos["instrument"]
        
        if is_forex(instrument):
            original_position = pos["target_position"]
            new_position = original_position * multiplier
            
            # Make a copy of the position with updated target_position
            updated_pos = pos.copy()
            updated_pos["target_position_original"] = original_position
            updated_pos["target_position"] = new_position
            balanced_positions.append(updated_pos)
        else:
            balanced_positions.append(pos)
    
    return balanced_positions

def calculate_target_positions(scores, usd_allocation, api=None, account_id=None):
    """
    Calculate target positions based on relative scores and USD allocation
    
    Args:
        scores: List of dicts with instrument and score information
        usd_allocation: Total USD amount to allocate
        api: Optional OANDA API client
        account_id: Optional OANDA account ID
        
    Returns:
        List of position records with target positions
    """
    # Extract scores and calculate absolute sum
    rel_scores = [abs(record.get("rel_buy_sell_score", 0)) for record in scores]
    sum_rel_scores = sum(rel_scores)
    
    if sum_rel_scores == 0:
        logger.warning("Sum of relative scores is zero, cannot allocate positions")
        return []
    
    # Calculate scalar for USD allocation
    scalar = usd_allocation / sum_rel_scores
    
    # Calculate target positions
    target_positions = []
    for record in scores:
        instrument = record.get("instrument")
        latest_price = record.get("latest_price")
        rel_score = record.get("rel_buy_sell_score", 0)
        
        # Calculate USD amount to allocate to this instrument
        usd_amount = scalar * abs(rel_score)
        
        # Calculate target position size
        target_position = get_target_position_amount(
            instrument, 
            latest_price, 
            usd_amount * (1 if rel_score >= 0 else -1),
            api,
            account_id
        )
        
        # Skip negative positions for crypto
        if is_crypto(instrument) and target_position < 0:
            target_position = 0
        
        # Create position record
        position_record = {
            "instrument": instrument,
            "latest_price": latest_price,
            "rel_score": rel_score,
            "usd_amount": usd_amount,
            "target_position": target_position,
            "direction": "LONG" if target_position > 0 else "SHORT"
        }
        
        target_positions.append(position_record)
    
    # Apply forex multiplier
    balanced_positions = apply_forex_multiplier(target_positions)
    
    return balanced_positions

def convert_target_positions_to_oanda_format(target_positions):
    """
    Convert target positions to the format expected by sync_positions.py
    
    Args:
        target_positions: List of position records from calculate_target_positions
        
    Returns:
        Dictionary with positions in the format expected by sync_positions.py
    """
    positions = []
    
    for pos in target_positions:
        instrument = pos["instrument"]
        target_position = pos["target_position"]
        
        if target_position == 0:
            direction = "NEUTRAL"
        else:
            direction = "LONG" if target_position > 0 else "SHORT"
        
        position_record = {
            "instrument": instrument,
            "direction": direction,
            "position_size": abs(target_position),
            "usd_amount": pos.get("usd_amount", 0)
        }
        
        positions.append(position_record)
    
    return {
        "account_size": 1000.0,  # Default value
        "risk_amount": 50.0,     # Default value
        "positions": positions
    }

# Testing function
class PositionSizer:
    """
    Simple position sizer that converts trading signals to position sizes
    """
    def __init__(self, account_size=1000.0, risk_percent=5.0):
        self.account_size = account_size
        self.risk_percent = risk_percent
        self.max_risk_amount = account_size * (risk_percent / 100.0)
    
    def convert_signals_to_positions(self, signals):
        """
        Convert trading signals to position sizes
        
        Args:
            signals: List of signal dictionaries with 'instrument', 'position', 'direction', 'strength'
            
        Returns:
            Dictionary with 'positions' and metadata
        """
        positions = {}
        total_allocation = 0
        
        for signal in signals:
            instrument = signal['instrument']
            position_strength = abs(signal['position'])
            
            # Calculate position size based on signal strength and risk
            if position_strength > 0.1:  # Only take positions above threshold
                # Allocate based on signal strength
                allocation = self.max_risk_amount * position_strength
                positions[instrument] = {
                    'size': allocation,
                    'direction': signal['direction'],
                    'strength': position_strength
                }
                total_allocation += allocation
        
        return {
            'positions': positions,
            'total_allocation': total_allocation,
            'account_size': self.account_size,
            'risk_percent': self.risk_percent
        }

def test_position_sizing():
    """Test position sizing calculations"""
    # Initialize API
    api_token = os.environ.get('OANDA_DEMO_KEY')
    account_id = os.environ.get('OANDA_DEMO_ACCOUNT_ID')
    
    if not api_token or not account_id:
        logger.error("API token or account ID not set")
        return
    
    api = API(access_token=api_token, environment="practice")
    
    # Test an instrument
    instrument = "EUR_USD"
    latest_price = get_latest_price(instrument, api, account_id)
    
    if not latest_price:
        logger.error(f"Could not get price for {instrument}")
        return
    
    usd_amount = 100.0
    target_position = get_target_position_amount(instrument, latest_price, usd_amount, api, account_id)
    
    logger.info(f"Instrument: {instrument}")
    logger.info(f"Latest price: {latest_price}")
    logger.info(f"USD amount: ${usd_amount}")
    logger.info(f"Target position: {target_position}")
    logger.info(f"With forex multiplier: {target_position * 25}")

if __name__ == "__main__":
    test_position_sizing() 