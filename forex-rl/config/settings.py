# config/settings.py
import os
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class ModelConfig:
    """Neural network model configuration"""
    input_dim: int = 300  # Updated: 20 pairs × 15 Fibonacci periods
    hidden_dims: List[int] = field(default_factory=lambda: [512, 256, 128])
    output_dim: int = 20  # Position sizing for each forex pair
    activation: str = "relu"
    dropout: float = 0.1
    batch_norm: bool = True

@dataclass
class TrainingConfig:
    """RL training configuration"""
    algorithm: str = "PPO"  # PPO, A2C, SAC
    learning_rate: float = 1e-4
    batch_size: int = 64
    epochs: int = 1000
    gamma: float = 0.99  # Discount factor
    entropy_weight: float = 0.01  # Entropy regularization
    value_loss_weight: float = 0.5  # Value function loss weight
    max_grad_norm: float = 0.5  # Gradient clipping
    
    # PPO specific
    ppo_epochs: int = 4
    clip_epsilon: float = 0.2
    gae_lambda: float = 0.95
    buffer_size: int = 2048

@dataclass
class RewardConfig:
    """Reward function configuration"""
    beta: float = 0.95  # DSR decay rate
    entropy_penalty: bool = True
    confidence_weighting: bool = True
    reward_clipping: Tuple[float, float] = (-10.0, 10.0)

@dataclass
class DataConfig:
    """Data processing configuration"""
    lookback_days: int = 5000  # Historical data to fetch
    normalization_window: int = 252  # Rolling window for normalization (1 year)
    fibonacci_periods: List[int] = field(
        default_factory=lambda: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
    )
    missing_data_strategy: str = 'forward_fill'  # Strategy for missing historical data

@dataclass
class TradingConfig:
    """Trading execution configuration"""
    initial_balance: float = 10000.0
    transaction_cost: float = 0.0002  # 2 basis points
    max_episode_steps: int = 1000
    position_limit: float = 0.1  # Maximum position size per pair
    total_exposure_limit: float = 2.0  # Maximum total exposure

@dataclass
class SystemConfig:
    """Main system configuration"""
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    data: DataConfig = field(default_factory=DataConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)

    # Environment variables
    oanda_api_key: str = field(default_factory=lambda: os.getenv('OANDA_DEMO_KEY', ''))
    oanda_account_id: str = field(default_factory=lambda: os.getenv('OANDA_DEMO_ACCOUNT_ID', ''))
    oanda_environment: str = field(default_factory=lambda: os.getenv('OANDA_ENVIRONMENT', 'practice'))

    # Paths
    data_dir: str = "data"
    model_dir: str = "models"
    log_dir: str = "logs"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Global configuration instance
config = SystemConfig()

# Validation
def validate_config():
    """Validate configuration consistency"""
    assert config.model.input_dim == 300, f"Expected 300 input features, got {config.model.input_dim}"
    assert config.model.output_dim == 20, f"Expected 20 output features, got {config.model.output_dim}"
    assert len(config.data.fibonacci_periods) == 15, f"Expected 15 Fibonacci periods, got {len(config.data.fibonacci_periods)}"
    
    if not config.oanda_api_key:
        print("Warning: OANDA_DEMO_KEY environment variable not set")
    if not config.oanda_account_id:
        print("Warning: OANDA_DEMO_ACCOUNT_ID environment variable not set")

# Run validation on import
validate_config() 