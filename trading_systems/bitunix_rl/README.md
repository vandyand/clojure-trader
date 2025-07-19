# Bitunix RL Trading System

## Overview

This project implements a Reinforcement Learning (RL) based trading system for cryptocurrency perpetual futures on Bitunix. The system uses the same core architecture as our Forex RL system but is adapted for Bitunix's API and perpetual futures trading mechanics.

## System Architecture

### 1. Data Collection Layer

- **BitunixClient**: Uses existing implementation from `bitunix/` directory
  - Handles authentication and rate limiting
  - Fetches OHLCV data for perpetual futures
  - Manages order execution and position management
  - Retrieves account information and balance updates
  - Supports WebSocket connections for real-time data

### 2. Feature Engineering

- **FibonacciFeatureEngineer**: Calculates 300 input features using:
  - 15 Fibonacci periods: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
  - Feature formula: ln(price*t / price*{t-fib_period})
  - Uses close prices for consistency
  - 20 trading pairs × 15 periods = 300 input nodes

### 3. Trading Pairs

The system trades the 20 highest liquidity USDT-denominated perpetual futures:

1. BTC/USDT
2. ETH/USDT
3. SOL/USDT
4. DOGE/USDT
5. USDC/USDT
6. FDUSD/USDT
7. XRP/USDT
8. MNT/USDT
9. PEPE/USDT
10. TRUMP/USDT
11. SUI/USDT
12. NEXPACE/USDT
13. BNB/USDT
14. TRX/USDT
15. AAVE/USDT
16. WLD/USDT
17. WIF/USDT
18. ZBC/USDT
19. ADA/USDT
20. VIRTUAL/USDT

### 4. Neural Network Architecture

- **Input Layer**: 300 nodes (20 pairs × 15 Fibonacci periods)
- **Hidden Layer 1**: 128 nodes with ReLU activation
- **Hidden Layer 2**: 64 nodes with ReLU activation
- **Output Layer**: 41 nodes (20 pairs × 2 actions + 1 hold)
  - Each pair has long/short actions
  - Global hold action for all pairs

### 5. Reward Function

```python
reward = (
    position_pnl +                    # Unrealized PnL from open positions
    realized_pnl +                    # Realized PnL from closed positions
    transaction_costs +               # Trading fees and slippage
    funding_rate_payments +           # Perpetual futures funding rate payments
    liquidation_penalty               # Penalty for liquidated positions
)
```

### 6. Risk Management

- Initial account size: $480
- Risk tolerance: 5% ($24)
- Position sizing based on:
  - Account equity
  - Volatility of each pair
  - Maximum drawdown limits
  - Leverage constraints (up to 125x available)

### 7. Training Process

1. **Data Collection**

   - Fetch historical OHLCV data
   - Calculate Fibonacci features
   - Store in SQLite database

2. **Model Training**

   - Use PPO (Proximal Policy Optimization)
   - Batch size: 64
   - Learning rate: 0.0003
   - Gamma: 0.99
   - Lambda: 0.95
   - Epochs: 10
   - Clip range: 0.2

3. **Evaluation**
   - Backtesting on historical data
   - Forward testing on live market
   - Performance metrics:
     - Sharpe ratio
     - Maximum drawdown
     - Win rate
     - Profit factor

### 8. Deployment

- Real-time market data streaming
- Automated order execution
- Position monitoring and risk management
- Performance logging and monitoring

## Directory Structure

```
bitunix-rl/
├── data/
│   ├── feature_engineer.py
│   └── db/
│       ├── models.py
│       └── database.py
├── training/
│   ├── environment.py
│   ├── model.py
│   └── train.py
├── scripts/
│   ├── collect_data.py
│   ├── train_model.py
│   └── calculate_position_sizes.py
├── config/
│   └── settings.py
├── bitunix/           # Symlink to existing Bitunix client implementation
└── README.md
```

## Implementation Notes

### Bitunix API Integration

The project leverages the existing Bitunix API client implementation from the `bitunix/` directory, which provides:

1. **Market Data**

   - OHLCV data fetching
   - Order book depth
   - Recent trades
   - WebSocket support for real-time data

2. **Account Management**

   - Balance tracking
   - Position management
   - Margin requirements
   - Leverage settings

3. **Order Types**
   - Market orders
   - Limit orders
   - Stop orders
   - Take profit orders
   - Stop loss orders

### Perpetual Futures Specifics

1. **Funding Rate**

   - 8-hour funding periods
   - Rate calculation and payment
   - Impact on position PnL

2. **Leverage**

   - Dynamic leverage limits
   - Margin requirements
   - Liquidation price calculation

3. **Position Management**
   - Long/short positions
   - Position size limits
   - Cross/isolated margin modes

## Getting Started

### Prerequisites

- Python 3.8+
- Bitunix API credentials
- SQLite3
- Required Python packages (see requirements.txt)

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure Bitunix API credentials
4. Initialize the database: `python scripts/init_db.py`
5. Ensure the `bitunix/` directory is properly linked

### Usage

1. Collect historical data:

   ```bash
   python scripts/collect_data.py
   ```

2. Train the model:

   ```bash
   python scripts/train_model.py
   ```

3. Calculate position sizes:
   ```bash
   python scripts/calculate_position_sizes.py
   ```

## Risk Warning

This system involves trading cryptocurrency perpetual futures with leverage. Users should:

- Understand the risks of leveraged trading
- Be aware of liquidation risks
- Monitor positions regularly
- Start with small position sizes
- Never risk more than they can afford to lose

## License

MIT License
