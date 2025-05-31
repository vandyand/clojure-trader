import os
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class ModelConfig:
    input_dim: int = 300  # 20 forex pairs × 15 Fibonacci periods
    hidden_dims: List[int] = field(default_factory=lambda: [512, 256, 128])
    output_dim: int = 20  # Position sizes for each forex pair
    activation: str = "relu"
    dropout: float = 0.1
    batch_norm: bool = True

@dataclass
class TrainingConfig:
    algorithm: str = "PPO"
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
    lookback_days: int = 5000
    normalization_window: int = 252
    fibonacci_periods: List[int] = field(
        default_factory=lambda: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
    )
    missing_data_strategy: str = 'forward_fill'  # Default strategy

@dataclass
class SystemConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    data: DataConfig = field(default_factory=DataConfig)

    # Environment variables
    oanda_api_key: str = field(default_factory=lambda: os.getenv('OANDA_DEMO_KEY', ''))
    oanda_account_id: str = field(default_factory=lambda: os.getenv('OANDA_DEMO_ACCOUNT_ID', ''))
    oanda_environment: str = field(default_factory=lambda: os.getenv('OANDA_ENVIRONMENT', 'practice'))

    # Paths
    data_dir: str = "data"
    model_dir: str = "models"
    log_dir: str = "logs"

# Global configuration instance
config = SystemConfig()
