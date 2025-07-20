# Crypto RL Trading System

A reinforcement learning trading system for cryptocurrencies that uses both crypto and ETF market data to generate target position sizes for the top 20 most liquid crypto pairs.

## Overview

This system is based on the existing forex RL trading system but adapted for cryptocurrency trading. It combines:

- **20 Top Liquid Crypto Pairs** (via Bitunix API)
- **34 ETF Symbols** (via yfinance)
- **Fusion Autoencoder** for feature compression
- **Reinforcement Learning Policy Network** for position sizing
- **Differential Sharpe Ratio** reward function

## Architecture

### Data Sources

- **Crypto Data**: 20 most liquid USDT pairs from Bitunix

  - BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT, USDCUSDT, FDUSDUSDT, XRPUSDT, MNTUSDT, PEPEUSDT, TRUMPUSDT, SUIUSDT, NEXPACEUSDT, BNBUSDT, TRXUSDT, AAVEUSDT, WLDUSDT, WIFUSDT, ZBCUSDT, ADAUSDT, VIRTUALUSDT

- **ETF Data**: 34 ETF symbols via yfinance
  - ASHR, BND, BTC-USD, BWX, CEW, CYB, DBA, DBC, DIA, EEM, EFA, EMB, EWJ, EWZ, EZU, FXB, FXE, FXF, FXY, GLD, IEF, QQQ, SHY, SLV, SPY, TLT, UNG, USO, UUP, VIXY, VNQ, XLE, XLF, XLI

### System Components

1. **Data Fetcher** (`data_fetcher.py`)

   - Fetches crypto data from Bitunix API
   - Fetches ETF data from yfinance
   - Calculates technical indicators and features

2. **Feature Engineering** (`feature_engineering.py`)

   - Calculates 23+ features per instrument
   - Moving averages, RSI, Bollinger Bands, volume indicators
   - Total input dimension: 54 instruments × 23 features = 1,242 features

3. **Fusion Autoencoder** (`policy_network.py`)

   - Compresses 1,242 features to 149-dimensional bottleneck
   - Uses LeakyReLU activation and BatchNorm
   - Provides robust feature representation

4. **Policy Network** (`policy_network.py`)

   - Takes autoencoder bottleneck as input
   - Outputs position sizes for 20 crypto pairs
   - Supports both long and short positions
   - Uses PPO-style training with entropy regularization

5. **Reward Calculator** (`policy_network.py`)

   - Implements Differential Sharpe Ratio (DSR)
   - Position entropy penalty for diversification
   - Confidence weighting based on Dirichlet concentration
   - Transaction cost modeling

6. **Trading System** (`trading_system.py`)
   - Main integration module
   - Training and evaluation loops
   - Signal generation and backtesting
   - Performance visualization

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional):

```bash
export BITUNIX_API_KEY=your_api_key
export BITUNIX_SECRET_KEY=your_secret_key
```

## Usage

### Training

Train the RL system:

```bash
python train_rl.py --epochs 100 --batch-size 32 --lr 1e-4
```

Test data fetcher before training:

```bash
python train_rl.py --test-data --epochs 50
```

### Trading System

Run the main trading system:

```bash
python trading_system.py --train --epochs 100
```

Evaluate trained model:

```bash
python trading_system.py --eval
```

Run simulation:

```bash
python trading_system.py --sim --sim-days 30
```

Generate current signals:

```bash
python trading_system.py
```

### Data Fetcher Testing

Test the data fetcher:

```bash
python data_fetcher.py
```

## Key Features

### Position Sizing

- **Dirichlet-inspired normalization**: Ensures position weights sum to 1
- **Entropy penalty**: Encourages diversification
- **Confidence weighting**: Uses concentration parameter for reward scaling

### Risk Management

- **Transaction costs**: 0.1% per trade (higher than forex due to crypto volatility)
- **Position limits**: Clamped to prevent extreme positions
- **Drawdown monitoring**: Tracks maximum drawdown during evaluation

### Reward Function

- **Differential Sharpe Ratio**: Online optimization of risk-adjusted returns
- **Portfolio return**: Direct P&L from position changes
- **Entropy regularization**: Balances exploration vs exploitation

## Model Architecture

### Autoencoder

- **Input**: 1,242 features (54 instruments × 23 features)
- **Encoder**: 621 → 310 → 149 (with LeakyReLU + BatchNorm)
- **Bottleneck**: 149 dimensions (tanh activation)
- **Decoder**: 149 → 310 → 621 → 1,242

### Policy Network

- **Input**: 149-dimensional bottleneck
- **Hidden**: 256 → 128 (LeakyReLU + LayerNorm + Dropout)
- **Output**: 20 position means (one per crypto pair)
- **Action Distribution**: Normal distribution with learned std devs

### Value Network

- **Input**: 149-dimensional bottleneck
- **Hidden**: 256 → 128 (LeakyReLU + LayerNorm)
- **Output**: Single value estimate

## Training Process

1. **Data Collection**: Fetch historical data for all instruments
2. **Feature Engineering**: Calculate technical indicators
3. **Autoencoder Training**: Compress features to bottleneck
4. **RL Training**: Train policy and value networks
5. **Evaluation**: Backtest on historical data
6. **Deployment**: Generate live trading signals

## Performance Metrics

- **Total Return**: Cumulative portfolio return
- **Sharpe Ratio**: Risk-adjusted return measure
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Average Trade Return**: Mean return per trade

## File Structure

```
crypto_rl/
├── constants.py              # Crypto pairs and ETF symbols
├── data_fetcher.py           # Market data fetching and feature calculation
├── feature_engineering.py    # Technical indicator calculations
├── policy_network.py         # RL networks and reward calculation
├── trading_system.py         # Main trading system integration
├── train_rl.py              # Training script
├── data/
│   └── fetch_etf_data.py    # ETF data fetching utilities
├── models/                  # Saved model checkpoints
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Differences from Forex System

1. **Data Sources**: Uses Bitunix for crypto instead of OANDA for forex
2. **Instruments**: 20 crypto pairs instead of 20 forex pairs
3. **Transaction Costs**: Higher (0.1% vs 0.05%) due to crypto volatility
4. **Position Sizing**: Supports both long and short positions
5. **Market Hours**: Crypto trades 24/7 vs forex market hours

## Future Enhancements

- [ ] Real-time data streaming
- [ ] Multi-timeframe analysis
- [ ] Advanced risk management
- [ ] Portfolio optimization
- [ ] Live trading integration
- [ ] Performance attribution analysis

## License

This project is part of the larger trading system repository.
