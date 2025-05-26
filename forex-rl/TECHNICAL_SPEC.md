# Forex RL Trading System - Technical Specification

## 📋 Document Overview

**Version**: 1.0  
**Date**: 2024-01-XX  
**Status**: Draft  
**Authors**: Development Team

This document provides detailed technical specifications for the Forex RL Trading System, including architecture, algorithms, data structures, and implementation details.

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Layer    │    │  Model Layer    │    │ Trading Layer   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ OANDA API   │ │    │ │ RL Agent    │ │    │ │ Position    │ │
│ │ Client      │ │    │ │             │ │    │ │ Manager     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Feature     │ │    │ │ Neural      │ │    │ │ Risk        │ │
│ │ Engineer    │ │    │ │ Network     │ │    │ │ Manager     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Data        │ │    │ │ Reward      │ │    │ │ Order       │ │
│ │ Validator   │ │    │ │ Function    │ │    │ │ Executor    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Interaction Flow

```
Data Fetching → Feature Engineering → Model Inference → Position Sizing → Order Execution
     ↓               ↓                    ↓              ↓              ↓
  Validation    Normalization      Action Sampling   Risk Checks   Execution
     ↓               ↓                    ↓              ↓              ↓
   Caching        Storage           Reward Calculation  Logging    Monitoring
```

---

## 📊 Data Specifications

### Input Data Structure

#### Forex Pairs (20 instruments)

```python
FOREX_PAIRS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]
```

#### Fibonacci Sequence (12 lookback periods)

```python
FIBONACCI_PERIODS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
```

#### Feature Calculation

For each forex pair `i` and Fibonacci period `j`:

```python
feature[i][j] = ln(price_t[i] / price_{t-fib_j}[i])
```

**Total Features**: 20 pairs × 12 periods = 240 features

### Data Schema

#### Raw OANDA Data

```python
@dataclass
class OandaCandle:
    time: datetime
    instrument: str
    granularity: str  # 'D' for daily
    open: float
    high: float
    low: float
    close: float
    volume: int
```

#### Processed Feature Vector

```python
@dataclass
class FeatureVector:
    timestamp: datetime
    features: np.ndarray  # Shape: (240,)
    pair_names: List[str]  # Length: 20
    fibonacci_periods: List[int]  # Length: 12

    def validate(self) -> bool:
        return (
            self.features.shape == (240,) and
            len(self.pair_names) == 20 and
            len(self.fibonacci_periods) == 12
        )
```

---

## 🧠 Model Architecture

### Neural Network Specification

#### Network Topology

```python
class ForexRLNetwork(nn.Module):
    def __init__(self):
        super().__init__()

        # Input layer: 240 features
        self.input_layer = nn.Linear(240, 512)
        self.input_bn = nn.BatchNorm1d(512)
        self.input_dropout = nn.Dropout(0.1)

        # Hidden layers
        self.hidden1 = nn.Linear(512, 256)
        self.hidden1_bn = nn.BatchNorm1d(256)
        self.hidden1_dropout = nn.Dropout(0.1)

        self.hidden2 = nn.Linear(256, 128)
        self.hidden2_bn = nn.BatchNorm1d(128)
        self.hidden2_dropout = nn.Dropout(0.1)

        # Output layer: 20 position values
        self.output_layer = nn.Linear(128, 20)

        # Activation function
        self.activation = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input processing
        x = self.activation(self.input_bn(self.input_layer(x)))
        x = self.input_dropout(x)

        # Hidden layer 1
        x = self.activation(self.hidden1_bn(self.hidden1(x)))
        x = self.hidden1_dropout(x)

        # Hidden layer 2
        x = self.activation(self.hidden2_bn(self.hidden2(x)))
        x = self.hidden2_dropout(x)

        # Output layer (no activation for continuous values)
        x = self.output_layer(x)

        return x
```

#### Model Parameters

- **Total Parameters**: ~200K parameters
- **Memory Usage**: ~50MB (including gradients)
- **Inference Time**: <10ms per forward pass
- **Training Batch Size**: 64-128 samples

### Reinforcement Learning Algorithm

#### PPO (Proximal Policy Optimization) Configuration

```python
PPO_CONFIG = {
    'learning_rate': 1e-4,
    'gamma': 0.99,           # Discount factor
    'gae_lambda': 0.95,      # GAE parameter
    'clip_epsilon': 0.2,     # PPO clipping parameter
    'entropy_weight': 0.01,  # Entropy regularization
    'value_loss_weight': 0.5, # Value function loss weight
    'max_grad_norm': 0.5,    # Gradient clipping
    'ppo_epochs': 4,         # PPO update epochs
    'batch_size': 64,        # Training batch size
    'buffer_size': 2048      # Experience buffer size
}
```

#### Alternative: A2C (Advantage Actor-Critic) Configuration

```python
A2C_CONFIG = {
    'learning_rate': 1e-4,
    'gamma': 0.99,
    'entropy_weight': 0.01,
    'value_loss_weight': 0.5,
    'max_grad_norm': 0.5,
    'n_steps': 5,            # N-step returns
    'batch_size': 32
}
```

---

## 🎯 Reward Function Specification

### Mathematical Formulation

The reward function implements the algorithm from `reward-info.md`:

#### Step 1: Position Normalization

```python
def normalize_positions(raw_outputs: np.ndarray) -> np.ndarray:
    """
    Normalize positions to control total exposure while preserving sign.

    Args:
        raw_outputs: Raw model outputs [20]

    Returns:
        Normalized positions [20]
    """
    total_exposure = np.sum(np.abs(raw_outputs)) + 1e-8
    scaling_factor = 0.5  # Allow for larger effective positions
    return raw_outputs / (total_exposure * scaling_factor)
```

#### Step 2: Entropy Penalty

```python
def position_entropy(positions: np.ndarray) -> Tuple[float, float]:
    """
    Calculate position entropy using absolute values.

    Returns:
        entropy: Position entropy
        normalized_entropy: Entropy normalized by log(n_instruments)
    """
    abs_pos = np.abs(positions)
    p = abs_pos / (np.sum(abs_pos) + 1e-8)
    entropy = -np.sum(p * np.log(p + 1e-8))
    normalized_entropy = entropy / np.log(len(positions))
    return entropy, normalized_entropy

def apply_entropy_penalty(positions: np.ndarray,
                         normalized_entropy: float) -> Tuple[np.ndarray, float]:
    """Apply entropy-based scaling to positions."""
    scaling_factor = 1.0 - (normalized_entropy * 0.5)  # Reduced penalty
    return positions * scaling_factor, scaling_factor
```

#### Step 3: Portfolio Return

```python
def portfolio_return(final_positions: np.ndarray,
                    price_changes: np.ndarray) -> float:
    """Calculate portfolio return from positions and price changes."""
    return np.sum(final_positions * price_changes)
```

#### Step 4: Differential Sharpe Ratio

```python
def calculate_dsr(returns: torch.Tensor,
                 mu_prev: float,
                 sigma_sq_prev: float,
                 beta: float = 0.95) -> Tuple[float, float, float]:
    """
    Calculate Differential Sharpe Ratio with exponential moving averages.

    Returns:
        dsr: Differential Sharpe ratio
        mu_t: Updated mean
        sigma_sq_t: Updated variance
    """
    mean_return = returns.mean()

    # Update statistics
    mu_t = mu_prev + beta * (mean_return - mu_prev)
    sigma_sq_t = sigma_sq_prev + beta * (mean_return**2 - sigma_sq_prev)

    # Calculate DSR
    delta = mean_return - mu_prev
    numerator = beta * delta - 0.5 * (beta**2) * sigma_sq_prev
    denominator = (sigma_sq_prev + beta * delta**2)**1.5 + 1e-12
    dsr = numerator / denominator

    return dsr, mu_t, sigma_sq_t
```

#### Step 5: Confidence Weighting

```python
def confidence_weighted_reward(dsr: float, total_exposure: float) -> Tuple[float, float]:
    """Apply confidence weighting based on total position exposure."""
    confidence = 1.0 - 1.0 / (total_exposure + 1.0)
    return dsr * confidence, confidence
```

### Complete Reward Pipeline

```python
class RewardCalculator:
    def __init__(self, n_instruments: int = 20, beta: float = 0.95):
        self.n_instruments = n_instruments
        self.beta = beta
        self.mu = 0.0  # Mean return
        self.sigma_sq = 0.0001  # Initial variance

    def calculate_reward(self,
                        raw_outputs: np.ndarray,
                        price_changes: np.ndarray) -> Dict[str, float]:
        """Complete reward calculation pipeline."""

        # 1. Normalize positions
        positions = self.normalize_positions(raw_outputs)
        total_exposure = np.sum(np.abs(positions))

        # 2. Apply entropy penalty
        entropy, norm_entropy = self.position_entropy(positions)
        final_positions, scaling = self.apply_entropy_penalty(positions, norm_entropy)

        # 3. Calculate portfolio return
        R_t = self.portfolio_return(final_positions, price_changes)

        # 4. Update DSR
        dsr, self.mu, self.sigma_sq = self.calculate_dsr(
            torch.tensor([R_t]), self.mu, self.sigma_sq, self.beta
        )

        # 5. Apply confidence weighting
        reward, confidence = self.confidence_weighted_reward(dsr, total_exposure)

        # 6. Clip reward
        clipped_reward = np.clip(reward, -10.0, 10.0)

        return {
            'raw_outputs': raw_outputs,
            'positions': positions,
            'final_positions': final_positions,
            'portfolio_return': R_t,
            'differential_sharpe': dsr,
            'confidence_weight': confidence,
            'final_reward': reward,
            'clipped_reward': clipped_reward,
            'total_exposure': total_exposure,
            'entropy': entropy,
            'normalized_entropy': norm_entropy
        }
```

---

## 🔄 Training Environment

### Trading Environment Specification

```python
class ForexTradingEnvironment:
    def __init__(self,
                 data: pd.DataFrame,
                 initial_balance: float = 10000.0,
                 transaction_cost: float = 0.0002,
                 max_episode_steps: int = 1000):

        self.data = data
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.max_episode_steps = max_episode_steps

        # State variables
        self.current_step = 0
        self.balance = initial_balance
        self.positions = np.zeros(20)
        self.portfolio_value = initial_balance

        # Reward calculator
        self.reward_calculator = RewardCalculator()

    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.current_step = 0
        self.balance = self.initial_balance
        self.positions = np.zeros(20)
        self.portfolio_value = self.initial_balance
        return self._get_observation()

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute one trading step."""

        # Get current market data
        current_data = self.data.iloc[self.current_step]
        price_changes = self._calculate_price_changes()

        # Calculate reward
        reward_info = self.reward_calculator.calculate_reward(action, price_changes)
        reward = reward_info['clipped_reward']

        # Update portfolio
        self._update_portfolio(action, price_changes)

        # Check if episode is done
        self.current_step += 1
        done = (
            self.current_step >= len(self.data) - 1 or
            self.current_step >= self.max_episode_steps or
            self.portfolio_value <= 0.1 * self.initial_balance  # Stop loss
        )

        # Get next observation
        next_obs = self._get_observation() if not done else np.zeros(240)

        info = {
            'portfolio_value': self.portfolio_value,
            'positions': self.positions.copy(),
            'reward_info': reward_info
        }

        return next_obs, reward, done, info

    def _get_observation(self) -> np.ndarray:
        """Get current market observation (240 features)."""
        if self.current_step >= len(self.data):
            return np.zeros(240)

        # Extract features for current timestep
        features = self.data.iloc[self.current_step].values
        return features.astype(np.float32)

    def _calculate_price_changes(self) -> np.ndarray:
        """Calculate price changes for current step."""
        if self.current_step == 0:
            return np.zeros(20)

        current_prices = self.data.iloc[self.current_step, :20]  # First 20 features are prices
        previous_prices = self.data.iloc[self.current_step - 1, :20]

        price_changes = (current_prices - previous_prices) / previous_prices
        return price_changes.values

    def _update_portfolio(self, action: np.ndarray, price_changes: np.ndarray):
        """Update portfolio based on action and price changes."""

        # Calculate position changes
        position_changes = action - self.positions

        # Apply transaction costs
        transaction_costs = np.sum(np.abs(position_changes)) * self.transaction_cost

        # Update positions
        self.positions = action.copy()

        # Calculate portfolio return
        portfolio_return = np.sum(self.positions * price_changes)

        # Update portfolio value
        self.portfolio_value *= (1 + portfolio_return - transaction_costs)

        # Update balance
        self.balance = self.portfolio_value - np.sum(np.abs(self.positions))
```

---

## 📡 Data Pipeline

### OANDA API Integration

```python
class OandaDataClient:
    def __init__(self, api_key: str, account_id: str, environment: str = "practice"):
        self.api = oandapyV20.API(access_token=api_key, environment=environment)
        self.account_id = account_id

    def fetch_historical_data(self,
                            instrument: str,
                            granularity: str = "D",
                            count: int = 5000) -> pd.DataFrame:
        """Fetch historical candlestick data."""

        params = {
            "granularity": granularity,
            "count": count
        }

        request = instruments.InstrumentsCandles(
            instrument=instrument,
            params=params
        )

        response = self.api.request(request)
        candles = response.get('candles', [])

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
        df.set_index('time', inplace=True)
        return df
```

### Feature Engineering Pipeline

```python
class FibonacciFeatureEngineer:
    def __init__(self, fibonacci_periods: List[int] = None):
        self.fibonacci_periods = fibonacci_periods or [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]

    def calculate_features(self, price_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate Fibonacci-based features for all forex pairs."""

        all_features = []
        feature_names = []

        for pair in FOREX_PAIRS:
            if pair not in price_data:
                continue

            df = price_data[pair]
            pair_features = []

            for period in self.fibonacci_periods:
                if len(df) > period:
                    # Calculate ln(price_t / price_{t-period})
                    feature = np.log(df['close'] / df['close'].shift(period))
                    pair_features.append(feature)
                    feature_names.append(f"{pair}_fib_{period}")
                else:
                    # Not enough data for this period
                    pair_features.append(pd.Series(0.0, index=df.index))
                    feature_names.append(f"{pair}_fib_{period}")

            if pair_features:
                all_features.extend(pair_features)

        # Combine all features
        feature_df = pd.concat(all_features, axis=1)
        feature_df.columns = feature_names

        # Handle missing values
        feature_df = feature_df.fillna(0.0)

        return feature_df

    def normalize_features(self, features: pd.DataFrame,
                          window: int = 252) -> pd.DataFrame:
        """Apply rolling z-score normalization."""

        normalized = features.copy()

        for column in features.columns:
            rolling_mean = features[column].rolling(window=window, min_periods=1).mean()
            rolling_std = features[column].rolling(window=window, min_periods=1).std()

            normalized[column] = (features[column] - rolling_mean) / (rolling_std + 1e-8)

        return normalized
```

---

## 🔧 Configuration Management

### Configuration Schema

```python
@dataclass
class ModelConfig:
    input_dim: int = 240
    hidden_dims: List[int] = field(default_factory=lambda: [512, 256, 128])
    output_dim: int = 20
    activation: str = "relu"
    dropout: float = 0.1
    batch_norm: bool = True

@dataclass
class TrainingConfig:
    algorithm: str = "PPO"  # PPO, A2C, SAC
    learning_rate: float = 1e-4
    batch_size: int = 64
    epochs: int = 1000
    gamma: float = 0.99
    entropy_weight: float = 0.01
    value_loss_weight: float = 0.5
    max_grad_norm: float = 0.5

@dataclass
class RewardConfig:
    beta: float = 0.95
    entropy_penalty: bool = True
    confidence_weighting: bool = True
    reward_clipping: Tuple[float, float] = (-10.0, 10.0)

@dataclass
class DataConfig:
    forex_pairs: List[str] = field(default_factory=lambda: FOREX_PAIRS)
    fibonacci_periods: List[int] = field(default_factory=lambda: FIBONACCI_PERIODS)
    lookback_days: int = 5000
    normalization_window: int = 252

@dataclass
class SystemConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    data: DataConfig = field(default_factory=DataConfig)

    # Environment variables
    oanda_api_key: str = ""
    oanda_account_id: str = ""
    oanda_environment: str = "practice"

    # Paths
    data_dir: str = "data"
    model_dir: str = "models"
    log_dir: str = "logs"
```

---

## 🧪 Testing Strategy

### Unit Test Coverage

```python
# Test categories and expected coverage
TEST_COVERAGE = {
    'data/': {
        'oanda_client.py': 90,
        'feature_engineer.py': 95,
        'data_validator.py': 85
    },
    'models/': {
        'network.py': 95,
        'agent.py': 90,
        'reward.py': 95
    },
    'training/': {
        'environment.py': 90,
        'trainer.py': 85
    },
    'inference/': {
        'predictor.py': 90,
        'position_manager.py': 85
    }
}
```

### Performance Benchmarks

```python
PERFORMANCE_BENCHMARKS = {
    'data_fetching': {
        'max_latency_ms': 5000,  # OANDA API call
        'throughput_rps': 10     # Requests per second
    },
    'feature_engineering': {
        'max_latency_ms': 100,   # 240 features calculation
        'memory_usage_mb': 50    # Peak memory usage
    },
    'model_inference': {
        'max_latency_ms': 10,    # Forward pass
        'throughput_fps': 1000   # Inferences per second
    },
    'training': {
        'episodes_per_hour': 1000,  # Training throughput
        'memory_usage_gb': 2        # Peak training memory
    }
}
```

---

## 🚀 Deployment Specifications

### Docker Configuration

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV OANDA_ENVIRONMENT=practice

# Expose port for monitoring
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["python", "scripts/train.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: forex-rl-training
spec:
  replicas: 1
  selector:
    matchLabels:
      app: forex-rl
  template:
    metadata:
      labels:
        app: forex-rl
    spec:
      containers:
        - name: forex-rl
          image: forex-rl:latest
          resources:
            requests:
              memory: "2Gi"
              cpu: "1000m"
            limits:
              memory: "4Gi"
              cpu: "2000m"
          env:
            - name: OANDA_API_KEY
              valueFrom:
                secretKeyRef:
                  name: oanda-credentials
                  key: api-key
            - name: OANDA_ACCOUNT_ID
              valueFrom:
                secretKeyRef:
                  name: oanda-credentials
                  key: account-id
          volumeMounts:
            - name: model-storage
              mountPath: /app/models
            - name: log-storage
              mountPath: /app/logs
      volumes:
        - name: model-storage
          persistentVolumeClaim:
            claimName: model-pvc
        - name: log-storage
          persistentVolumeClaim:
            claimName: log-pvc
```

---

## 📊 Monitoring & Observability

### Metrics Collection

```python
MONITORING_METRICS = {
    'system_metrics': [
        'cpu_usage_percent',
        'memory_usage_mb',
        'disk_usage_gb',
        'network_io_mbps'
    ],
    'application_metrics': [
        'inference_latency_ms',
        'training_loss',
        'reward_per_episode',
        'portfolio_value',
        'position_count',
        'api_call_success_rate'
    ],
    'business_metrics': [
        'sharpe_ratio',
        'max_drawdown',
        'win_rate',
        'profit_factor',
        'total_return'
    ]
}
```

### Alerting Rules

```python
ALERT_RULES = {
    'critical': {
        'api_failure_rate > 10%': 'OANDA API failures',
        'memory_usage > 90%': 'High memory usage',
        'max_drawdown > 20%': 'Excessive drawdown'
    },
    'warning': {
        'inference_latency > 100ms': 'Slow inference',
        'training_loss_increase > 50%': 'Training degradation',
        'position_concentration > 80%': 'High concentration risk'
    }
}
```

---

## 🔒 Security Considerations

### API Key Management

- Store API keys in environment variables or secure vaults
- Rotate keys regularly (monthly)
- Use separate keys for development and production
- Implement key validation and error handling

### Data Security

- Encrypt sensitive data at rest and in transit
- Implement access controls for model files
- Log all data access and modifications
- Regular security audits and penetration testing

### Model Security

- Validate all inputs to prevent adversarial attacks
- Implement model versioning and rollback capabilities
- Monitor for unusual model behavior
- Secure model deployment pipeline

---

## 📈 Performance Optimization

### Memory Optimization

- Use float32 instead of float64 for features
- Implement data streaming for large datasets
- Clear unused variables and call garbage collection
- Use memory mapping for large files

### Compute Optimization

- Vectorize operations using NumPy
- Use GPU acceleration for training (CUDA)
- Implement parallel data processing
- Optimize batch sizes for hardware

### Network Optimization

- Implement connection pooling for API calls
- Use compression for data transfer
- Cache frequently accessed data
- Implement retry logic with exponential backoff

---

This technical specification provides the foundation for implementing a robust, scalable, and maintainable Forex RL trading system. All components should be implemented following these specifications to ensure consistency and reliability.
