# Unified Futures RL Trading System

A comprehensive reinforcement learning trading system for cryptocurrency perpetual futures that combines the best elements from multiple trading systems into a unified, production-ready solution.

## 🎯 **Key Features**

- **Multi-Market Feature Fusion**: Combines crypto, ETF, and technical indicators
- **Fibonacci Sequence Features**: 300 features from 20 crypto pairs × 15 Fibonacci periods
- **Fusion Autoencoder**: Compresses 1,242 features to 149-dimensional bottleneck
- **Advanced Reward Function**: Differential Sharpe ratio with entropy penalty and confidence weighting
- **Long/Short Support**: Full support for both long and short positions
- **Perpetual Futures Trading**: Optimized for leveraged crypto futures trading
- **Real-time Capabilities**: Ready for live trading with proper risk management

## 🏗️ **Architecture Overview**

```
Input Features (1,242 dimensions)
├── Fibonacci Features (300)
│   ├── 20 crypto pairs × 15 Fibonacci periods
│   └── Formula: ln(price_t / price_{t-fib_period})
├── ETF Technical Indicators (782)
│   ├── 34 ETFs × 23 technical indicators
│   └── RSI, MACD, Bollinger Bands, ATR, etc.
└── Crypto Technical Indicators (160)
    ├── 20 crypto pairs × 8 technical indicators
    └── Core momentum and volatility indicators

↓ Fusion Autoencoder (1,242 → 149)

Bottleneck Representation (149 dimensions)
├── Scaled Tanh inputs for stability
├── LeakyReLU + BatchNorm layers
└── Progressive compression: 1,242 → 621 → 310 → 149

↓ Policy Network (149 → 20)

Position Signals (20 dimensions)
├── Positive values: Long positions
├── Negative values: Short positions
└── Support for all 20 crypto futures pairs

↓ Reward Calculation

Advanced Reward Function
├── Differential Sharpe Ratio (DSR)
├── Position entropy penalty for diversification
├── Confidence weighting based on Dirichlet concentration
└── Transaction cost modeling
```

## 📊 **Trading Pairs**

### **Crypto Futures (20 pairs)**

```
BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT, USDCUSDT,
FDUSDUSDT, XRPUSDT, MNTUSDT, PEPEUSDT, TRUMPUSDT,
SUIUSDT, NEXPACEUSDT, BNBUSDT, TRXUSDT, AAVEUSDT,
WLDUSDT, WIFUSDT, ZBCUSDT, ADAUSDT, VIRTUALUSDT
```

### **ETF Correlation (34 symbols)**

```
SPY, QQQ, GLD, TLT, DIA, EEM, EFA, IEF, SHY, VNQ,
XLE, XLF, XLI, VIXY, UUP, ASHR, BND, BTC-USD, BWX,
CEW, CYB, DBA, DBC, EMB, EWJ, EWZ, EZU, FXB, FXE,
FXF, FXY, SLV, UNG, USO
```

## 🧠 **Reward Function**

The system implements the sophisticated reward mechanism from `reward-info.md`:

### **Step 1: Position Normalization**

```python
# Split long/short positions
long_positions = max(raw_outputs, 0)
short_positions = max(-raw_outputs, 0)
alpha = long_positions + short_positions
alpha_0 = sum(alpha)

# Normalize positions
positions = alpha / alpha_0
positions = positions * sign(raw_outputs)  # Restore signs
```

### **Step 2: Entropy Penalty**

```python
# Calculate position entropy
abs_pos = abs(positions)
p = abs_pos / sum(abs_pos)
entropy = -sum(p * log(p))
normalized_entropy = entropy / log(n_instruments)

# Apply scaling factor
scaling_factor = 1 - normalized_entropy
final_positions = positions * scaling_factor
```

### **Step 3: Differential Sharpe Ratio**

```python
# Calculate DSR
delta = R_t - mu_prev
numerator = beta * delta - 0.5 * beta² * sigma²_prev
denominator = (sigma²_prev + beta * delta²)^(3/2)
dsr = numerator / denominator

# Update tracking variables
mu_prev = mu_prev + beta * delta
sigma²_prev = sigma²_prev + beta * (R_t² - sigma²_prev)
```

### **Step 4: Confidence Weighting**

```python
# Apply confidence weighting
confidence = 1 - 1/(alpha_0 + 1)
final_reward = dsr * confidence
```

## 🚀 **Quick Start**

### **Installation**

```bash
# Clone the repository
cd trading_systems/unified_futures_rl

# Install dependencies
pip install -r requirements.txt
```

### **Training**

```bash
# Train the system
python trading_system.py --train --epochs 100 --batch-size 64

# Train with custom autoencoder
python trading_system.py --train --epochs 100 --autoencoder-path models/fusion_autoencoder.pt
```

### **Evaluation**

```bash
# Evaluate trained model
python trading_system.py --eval

# Evaluate with custom model
python trading_system.py --eval --trader-path models/checkpoint_epoch_50.pt
```

### **Generate Trading Signals**

```python
from unified_futures_rl.trading_system import UnifiedFuturesTradingSystem

# Initialize system
trading_system = UnifiedFuturesTradingSystem(
    autoencoder_path='models/fusion_autoencoder.pt',
    trader_path='models/checkpoint_epoch_100.pt'
)

# Generate signals
signals = trading_system.generate_trading_signals(
    crypto_data=crypto_market_data,
    etf_data=etf_market_data
)

print("Position Signals:", signals['position_signals'])
print("Confidence Scores:", signals['confidence_scores'])
```

## 📈 **Performance Metrics**

The system tracks comprehensive performance metrics:

- **Rewards**: Training rewards and differential Sharpe ratios
- **Returns**: Portfolio returns and risk-adjusted performance
- **Entropy**: Position diversification and concentration
- **Losses**: Policy and value network training losses
- **Diversity**: Position diversity across instruments

## 🔧 **Configuration**

### **Trading Parameters**

```python
ACCOUNT_SIZE = 480.0  # USD
RISK_TOLERANCE_PERCENT = 5.0  # 5% risk tolerance
MAX_LEVERAGE = 125.0  # Maximum leverage available
TRANSACTION_COST_RATE = 0.001  # 0.1% per trade
```

### **Training Parameters**

```python
BATCH_SIZE = 64
LEARNING_RATE_ACTOR = 1e-4
LEARNING_RATE_CRITIC = 1e-3
GAMMA = 0.99  # Discount factor
ENTROPY_WEIGHT = 0.01  # Entropy regularization
```

### **Reward Parameters**

```python
DSR_BETA = 0.95  # Differential Sharpe Ratio decay rate
ENTROPY_SCALING = True  # Enable entropy penalty
CONFIDENCE_WEIGHTING = True  # Enable confidence weighting
```

## 📁 **File Structure**

```
unified_futures_rl/
├── __init__.py                 # Package initialization
├── constants.py               # System constants and configuration
├── feature_engineering.py     # Multi-market feature engineering
├── autoencoder.py             # Fusion autoencoder implementation
├── policy_network.py          # RL policy and value networks
├── reward_calculator.py       # Advanced reward function
├── trading_system.py          # Main trading system integration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── models/                    # Saved models and checkpoints
    ├── fusion_autoencoder.pt  # Trained autoencoder
    ├── checkpoint_epoch_*.pt  # Training checkpoints
    └── metrics_epoch_*.json   # Training metrics
```

## 🎮 **Usage Examples**

### **Training with Custom Data**

```python
from unified_futures_rl.trading_system import UnifiedFuturesTradingSystem

# Initialize system
trading_system = UnifiedFuturesTradingSystem()

# Train the system
trading_system.train(epochs=100, batch_size=64)

# Plot training progress
trading_system.plot_training_progress()

# Save checkpoint
trading_system.save_checkpoint(epoch=100)
```

### **Live Trading Integration**

```python
# Load trained system
trading_system = UnifiedFuturesTradingSystem(
    autoencoder_path='models/fusion_autoencoder.pt',
    trader_path='models/checkpoint_epoch_100.pt'
)

# Get real-time signals
while True:
    # Fetch current market data
    crypto_data = fetch_bitunix_data()
    etf_data = fetch_yfinance_data()

    # Generate signals
    signals = trading_system.generate_trading_signals(
        crypto_data=crypto_data,
        etf_data=etf_data
    )

    # Execute trades based on signals
    execute_trades(signals['final_positions'])

    time.sleep(60)  # Update every minute
```

## 🔍 **Advanced Features**

### **Feature Engineering**

- **Fibonacci Features**: Multi-period price ratios using Fibonacci sequence
- **Technical Indicators**: Comprehensive set of momentum and volatility indicators
- **Multi-Market Correlation**: ETF data for market regime detection
- **Robust Scaling**: Median-based normalization for outlier handling

### **Neural Network Architecture**

- **Scaled Tanh Inputs**: Improved gradient flow and stability
- **Layer Normalization**: Stable training across different market conditions
- **Dropout Regularization**: Prevents overfitting
- **Progressive Compression**: Efficient dimensionality reduction

### **Risk Management**

- **Position Limits**: Maximum 20% per instrument
- **Drawdown Protection**: 15% maximum drawdown limit
- **Volatility Scaling**: Dynamic position sizing
- **Transaction Costs**: Realistic cost modeling

## 📊 **Monitoring and Visualization**

The system provides comprehensive monitoring:

- **Training Progress**: Real-time metrics and loss curves
- **Position Heatmaps**: Visual representation of portfolio allocation
- **Performance Metrics**: Sharpe ratios, drawdowns, and win rates
- **Feature Analysis**: Importance and correlation analysis

## 🚨 **Risk Warnings**

This system involves trading cryptocurrency perpetual futures with leverage:

- **High Risk**: Leveraged trading can result in significant losses
- **Volatility**: Crypto markets are highly volatile
- **Liquidation Risk**: Leveraged positions can be liquidated
- **Technical Risk**: System failures can result in trading losses

**Never risk more than you can afford to lose.**

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests and documentation
5. Submit a pull request

## 📄 **License**

This project is part of the larger trading system repository and is licensed under the MIT License.

## 🔗 **Related Systems**

- **Forex RL System**: `trading_systems/rl/` - Forex trading with fusion autoencoder
- **Crypto RL System**: `trading_systems/crypto_rl/` - Spot crypto trading
- **Bitunix RL System**: `trading_systems/bitunix_rl/` - Perpetual futures planning

---

**Built with ❤️ using PyTorch, NumPy, and advanced ML techniques**
