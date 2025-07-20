"""
Crypto RL Trading System

A reinforcement learning trading system for cryptocurrencies that uses both crypto and ETF market data
to generate target position sizes for the top 20 most liquid crypto pairs.
"""

from .constants import CRYPTO_PAIRS_BY_LIQUIDITY, ETF_SYMBOLS
from .data_fetcher import CryptoMarketDataFetcher
from .feature_engineering import calculate_features
from .policy_network import CryptoRLTrader, PolicyNetwork, ValueNetwork, RewardCalculator
from .trading_system import CryptoTradingSystem

__version__ = "1.0.0"
__author__ = "Trading System Team"

__all__ = [
    "CRYPTO_PAIRS_BY_LIQUIDITY",
    "ETF_SYMBOLS", 
    "CryptoMarketDataFetcher",
    "calculate_features",
    "CryptoRLTrader",
    "PolicyNetwork",
    "ValueNetwork", 
    "RewardCalculator",
    "CryptoTradingSystem"
] 