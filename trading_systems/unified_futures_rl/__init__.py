"""
Unified Futures RL Trading System

A comprehensive reinforcement learning trading system for cryptocurrency perpetual futures
that combines:
- 20 top liquid crypto pairs (Bitunix perpetual futures)
- 34 ETF symbols (yfinance) for market correlation
- Fibonacci sequence features (300 features: 20 pairs × 15 periods)
- Fusion autoencoder for state representation (1,242 → 149 dimensions)
- Advanced reward function with differential Sharpe ratio, entropy penalty, and confidence weighting
- Support for both long and short positions

Key Features:
- Perpetual futures trading with leverage up to 125x
- Multi-market feature fusion (crypto + ETF correlation)
- Sophisticated position sizing with entropy penalties
- Real-time market data streaming
- Advanced risk management
"""

__version__ = "1.0.0"
__author__ = "Trading System Team" 