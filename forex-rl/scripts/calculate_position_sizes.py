#!/usr/bin/env python3
"""
Calculate position sizes based on NAV and risk tolerance
"""
import sys
import os
import argparse
import torch
import pickle
import logging
import numpy as np
from pathlib import Path
import requests
from typing import Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import create_agent
from config.settings import config
from data.oanda_client import OandaClient
from config.forex_pairs import FOREX_PAIRS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_account_nav() -> float:
    """Fetch current NAV from demo account"""
    try:
        client = OandaClient()
        account_summary = client.get_account_summary()
        nav = float(account_summary['NAV'])
        logger.info(f"Successfully fetched NAV from OANDA: ${nav:,.2f}")
        return nav
    except Exception as e:
        logger.error(f"Failed to fetch NAV: {e}")
        raise

def round_position_size(size: float, min_units: float = 0.0) -> float:
    """
    Round position size to nearest valid unit size
    
    Args:
        size: Raw position size in base currency
        min_units: Minimum position size in units
        
    Returns:
        Rounded position size in units
    """
    if min_units > 0.0:
        rounded = round(size / min_units) * min_units
        return float(rounded)
    else:
        return float(size)

def calculate_position_sizes(
    actions: np.ndarray,
    nav: float,
    risk_tolerance_pct: float = 5.0,
    min_units: float = 0.0
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Calculate position sizes based on NAV and risk tolerance
    
    Args:
        actions: Raw action values from model [-1, 1]
        nav: Current account NAV
        risk_tolerance_pct: Risk tolerance as percentage of NAV
        min_units: Minimum position size in units
        
    Returns:
        Tuple of (position_sizes, position_details)
        position_sizes: Scaled position sizes in base currency
        position_details: Dict with position details including risk allocation
    """
    # Calculate total risk amount
    risk_amount = nav * (risk_tolerance_pct / 100.0)
    
    # Get absolute values of actions and their sum
    abs_actions = np.abs(actions)
    total_abs_actions = np.sum(abs_actions)
    
    if total_abs_actions == 0:
        logger.warning("All actions are zero, no positions to size")
        return np.zeros_like(actions), {}
    
    # Scale actions to sum to risk_amount
    position_sizes = (abs_actions / total_abs_actions) * risk_amount
    
    # Apply original signs back to get long/short direction
    position_sizes = position_sizes * np.sign(actions)
    
    # For small accounts, we need to scale up the position sizes to meet minimum unit requirements
    # while maintaining relative proportions
    if min_units > 0.0:
        min_position_value = min_units * 0.0001  # Assuming 0.0001 is the minimum pip value
        if np.max(np.abs(position_sizes)) < min_position_value and np.max(np.abs(position_sizes)) > 0:
            scale_factor = min_position_value / np.max(np.abs(position_sizes))
            position_sizes = position_sizes * scale_factor
            logger.info(f"Scaled up positions by factor {scale_factor:.2f} to meet minimum unit requirements")
    
    # Round position sizes to nearest valid unit size
    rounded_sizes = np.array([round_position_size(abs(size), min_units) * np.sign(size) 
                            for size in position_sizes])
    
    # Calculate position details
    position_details = {
        'nav': nav,
        'risk_amount': risk_amount,
        'risk_tolerance_pct': risk_tolerance_pct,
        'total_exposure': np.sum(np.abs(rounded_sizes)),
        'max_position': np.max(np.abs(rounded_sizes)),
        'min_position': np.min(np.abs(rounded_sizes)),
        'num_positions': np.sum(np.abs(rounded_sizes) > 0),
        'long_positions': np.sum(rounded_sizes > 0),
        'short_positions': np.sum(rounded_sizes < 0)
    }
    
    return rounded_sizes, position_details

def post_orders_to_oanda(position_sizes, forex_pairs):
    """
    Post orders to OANDA demo account for each nonzero position size.
    Args:
        position_sizes: array of position sizes (signed, integer)
        forex_pairs: list of forex pair strings
    """
    client = OandaClient()
    results = []
    for size, pair in zip(position_sizes, forex_pairs):
        units = int(size)
        if units == 0:
            continue
        try:
            logger.info(f"Posting order: {pair} | Units: {units}")
            resp = client.place_order(
                instrument=pair,
                units=units,
                order_type="MARKET"
            )
            logger.info(f"Order result for {pair}: {resp}")
            results.append((pair, units, resp))
        except Exception as e:
            logger.error(f"Failed to post order for {pair}: {e}")
            results.append((pair, units, str(e)))
    return results

def main():
    parser = argparse.ArgumentParser(description="Calculate position sizes from model actions")
    parser.add_argument('--features', type=str, required=True, help='Path to features pickle file')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--risk_tolerance', type=float, default=5.0, help='Risk tolerance as percentage of NAV')
    parser.add_argument('--min_units', type=float, default=0.0, help='Minimum position size in units (0 for no rounding)')
    args = parser.parse_args()
    
    # Get current NAV
    nav = get_account_nav()
    logger.info(f"Current NAV: ${nav:,.2f}")
    
    # Load features and run inference
    logger.info(f"Loading features from {args.features}")
    features = pickle.load(open(args.features, 'rb'))
    if hasattr(features, 'values'):
        features = features.values
    latest_features = features[-1]
    
    # Load model and get actions
    logger.info(f"Loading model from {args.checkpoint}")
    agent = create_agent('PPO', state_dim=300, action_dim=20)
    agent.load_checkpoint(args.checkpoint)
    
    state = torch.tensor(latest_features, dtype=torch.float32).unsqueeze(0)
    actions, log_prob, value = agent.select_action(state, deterministic=True)
    actions = actions.squeeze(0).numpy()
    
    # Calculate position sizes
    position_sizes, details = calculate_position_sizes(
        actions=actions,
        nav=nav,
        risk_tolerance_pct=args.risk_tolerance,
        min_units=args.min_units
    )
    
    # Print results
    print("\nPosition Sizing Results:")
    print(f"NAV: ${details['nav']:,.2f}")
    print(f"Risk Amount ({args.risk_tolerance}%): ${details['risk_amount']:,.2f}")
    print(f"Total Exposure: ${details['total_exposure']:,.2f}")
    print(f"Number of Positions: {details['num_positions']}")
    print(f"Long Positions: {details['long_positions']}")
    print(f"Short Positions: {details['short_positions']}")
    print("\nPosition Sizes:")
    for i, (size, pair) in enumerate(zip(position_sizes, FOREX_PAIRS)):
        if abs(size) > 0:
            print(f"{pair}: {abs(size):,} units ({'LONG' if size > 0 else 'SHORT'})")

    # Post orders to OANDA demo account
    print("\nPosting orders to OANDA demo account...")
    order_results = post_orders_to_oanda(position_sizes, FOREX_PAIRS)
    print("\nOrder Results:")
    for pair, units, resp in order_results:
        print(f"{pair}: {units} units -> {resp}")

if __name__ == "__main__":
    main() 