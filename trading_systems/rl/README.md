# AI Trading System with Fusion Autoencoder and RL Policy

This directory contains a complete trading system that uses:

1. **Fusion Autoencoder** - A deep neural network that combines features from Forex and ETF markets into a compact latent representation with bottleneck size 149, using scaled tanh inputs for improved stability and representation power.

2. **RL Policy Network** - A reinforcement learning network that takes the autoencoder's bottleneck layer as input and produces trading decisions for 20 currency pairs.

3. **Custom Reward Mechanism** - Implements a sophisticated reward function with position normalization, entropy penalties, differential Sharpe ratio calculation, and confidence weighting.

## Key Components

- `autoencoder_fusion.py` - Implementation of the fusion autoencoder with scaled tanh inputs
- `policy_network.py` - Core RL framework with policy network and reward calculation
- `train_rl.py` - Training and evaluation framework
- `trading_system.py` - Complete trading system that ties everything together

## Usage

### Training the RL Policy

```bash
python rl/trading_system.py --train --epochs 50
```

### Evaluating the Policy

```bash
python rl/trading_system.py --eval
```

### Running a Trading Simulation

```bash
python rl/trading_system.py --sim --sim-days 30
```

### Generating Current Trading Signals

```bash
python rl/trading_system.py
```

## Methodology

### Fusion Autoencoder

- Combines features from Forex and ETF markets
- Uses scaled tanh inputs for better representation
- Bottleneck size of 149 provides optimal compression while preserving key market patterns
- Trained with regularization to prevent overfitting

### RL Policy Network

- Takes the autoencoder's bottleneck as input state
- Outputs trading positions for 20 currency pairs
- Uses a non-linear architecture with LayerNorm for stable training
- Trained using policy gradient methods with entropy regularization

### Reward Mechanism

1. **Position Calculation**:

   - Transforms raw outputs into long/short position confidence values
   - Normalizes positions using Dirichlet concentration parameter

2. **Entropy Penalty**:

   - Calculates position entropy to measure diversification
   - Applies scaling factor to penalize highly concentrated portfolios

3. **Performance Metrics**:

   - Uses Differential Sharpe Ratio (DSR) for more stable rewards
   - Applies exponential moving average for return and variance

4. **Confidence Weighting**:
   - Scales rewards based on model confidence
   - Clips rewards to prevent extreme values

## Results

The system demonstrates the ability to:

1. Learn meaningful market representations through the fusion autoencoder
2. Generate trading decisions across multiple currency pairs
3. Adapt to changing market conditions through ongoing training

## Future Improvements

1. Incorporate real market data feeds
2. Add prediction consistency penalties to reduce policy volatility
3. Implement risk constraints and portfolio optimization
4. Add Bayesian estimation for better uncertainty quantification
