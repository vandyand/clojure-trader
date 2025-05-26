# training/environment.py
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import torch
from typing import Dict, Tuple, Optional, Any, List
import logging
from dataclasses import dataclass
from enum import Enum

from data.feature_engineer import FibonacciFeatureEngineer
from data.data_validator import DataValidator
from models.reward import ForexRewardFunction
from config.settings import config
from config.forex_pairs import FOREX_PAIRS

logger = logging.getLogger(__name__)

class MarketState(Enum):
    """Market state enumeration"""
    NORMAL = "normal"
    VOLATILE = "volatile"
    TRENDING = "trending"
    SIDEWAYS = "sideways"

@dataclass
class TradingMetrics:
    """Trading performance metrics"""
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0
    total_fees: float = 0.0
    current_equity: float = 1.0
    peak_equity: float = 1.0

class ForexTradingEnvironment(gym.Env):
    """
    Gym-style Forex trading environment for RL training
    
    Features:
    - Realistic market simulation with transaction costs
    - Portfolio management and position tracking
    - Multiple episode termination conditions
    - Comprehensive state representation
    - Performance metrics tracking
    """
    
    def __init__(self,
                 data: pd.DataFrame = None,
                 initial_balance: float = 10000.0,
                 transaction_cost: float = 0.0001,  # 1 pip spread
                 max_position_size: float = 0.1,    # 10% max position per pair
                 max_episode_steps: int = 1000,
                 lookback_window: int = 100,
                 reward_function: ForexRewardFunction = None,
                 feature_engineer: FibonacciFeatureEngineer = None,
                 normalize_observations: bool = True,
                 include_market_state: bool = True,
                 risk_free_rate: float = 0.02):
        """
        Initialize Forex trading environment
        
        Args:
            data: Historical price data (OHLCV format)
            initial_balance: Starting account balance
            transaction_cost: Transaction cost per trade (as fraction)
            max_position_size: Maximum position size per instrument
            max_episode_steps: Maximum steps per episode
            lookback_window: Number of historical steps for state
            reward_function: Custom reward function
            feature_engineer: Feature engineering component
            normalize_observations: Whether to normalize observations
            include_market_state: Whether to include market state features
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
        """
        super().__init__()
        
        # Environment configuration
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.max_position_size = max_position_size
        self.max_episode_steps = max_episode_steps
        self.lookback_window = lookback_window
        self.normalize_observations = normalize_observations
        self.include_market_state = include_market_state
        self.risk_free_rate = risk_free_rate
        
        # Data and features
        self.data = data
        self.feature_engineer = feature_engineer or FibonacciFeatureEngineer()
        self.reward_function = reward_function or ForexRewardFunction()
        
        # Trading state
        self.current_step = 0
        self.current_balance = initial_balance
        self.positions = np.zeros(len(FOREX_PAIRS))  # Current positions
        self.equity_curve = []
        self.returns_history = []
        self.trades_history = []
        
        # Performance tracking
        self.metrics = TradingMetrics()
        self.episode_metrics = []
        
        # Market state tracking
        self.market_state = MarketState.NORMAL
        self.volatility_window = 20
        
        # Define action and observation spaces
        self._setup_spaces()
        
        # Prepare data if provided
        if data is not None:
            self._prepare_data()
        
        logger.info(f"Initialized ForexTradingEnvironment: {len(FOREX_PAIRS)} pairs, max_steps={max_episode_steps}")
    
    def _setup_spaces(self):
        """Setup action and observation spaces"""
        # Action space: continuous position sizing for each forex pair [-1, 1]
        # -1 = max short, 0 = no position, +1 = max long
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(len(FOREX_PAIRS),),
            dtype=np.float32
        )
        
        # Observation space: features + portfolio state + market state
        feature_dim = len(FOREX_PAIRS) * len(self.feature_engineer.fibonacci_periods)  # 300
        portfolio_dim = len(FOREX_PAIRS) + 3  # positions + balance + equity + drawdown
        market_dim = 4 if self.include_market_state else 0  # volatility, trend, momentum, regime
        
        obs_dim = feature_dim + portfolio_dim + market_dim
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )
        
        logger.info(f"Action space: {self.action_space.shape}, Observation space: {self.observation_space.shape}")
    
    def _prepare_data(self):
        """Prepare and validate data for training"""
        logger.info("Preparing trading data...")
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if isinstance(self.data, dict):
            for pair, df in self.data.items():
                if not all(col in df.columns for col in required_columns):
                    raise ValueError(f"Data for {pair} must contain columns: {required_columns}")
        else:
            if not all(col in self.data.columns for col in required_columns):
                raise ValueError(f"Data must contain columns: {required_columns}")
        # Calculate features for all data
        self.features = self._calculate_features()
        # Calculate market indicators
        self._calculate_market_indicators()
        # Determine valid episode start points (after lookback window)
        if isinstance(self.data, dict):
            # Use the length of the first pair's DataFrame
            first_df = next(iter(self.data.values()))
            data_len = len(first_df)
        else:
            data_len = len(self.data)
        self.valid_start_indices = list(range(
            self.lookback_window + max(self.feature_engineer.fibonacci_periods),
            data_len - self.max_episode_steps
        ))
        logger.info(f"Prepared {len(self.valid_start_indices)} valid episode start points")
    
    def _calculate_features(self) -> np.ndarray:
        """Calculate Fibonacci features for all data"""
        # For simplicity, assume data contains all forex pairs
        # In practice, you'd need to organize multi-instrument data
        if isinstance(self.data, dict):
            price_data_dict = self.data
        else:
            # Create dummy price data for all pairs (replace with real multi-instrument data)
            price_data_dict = {}
            for i, pair in enumerate(FOREX_PAIRS):
                pair_data = self.data.copy()
                noise_factor = 1.0 + (i * 0.01)  # Small variation between pairs
                for col in ['open', 'high', 'low', 'close']:
                    pair_data[col] *= noise_factor
                price_data_dict[pair] = pair_data
        # Calculate features
        features_df = self.feature_engineer.calculate_features_all_pairs(
            price_data_dict, 
            missing_data_strategy='forward_fill'
        )
        return features_df.values
    
    def _calculate_market_indicators(self):
        """Calculate market state indicators"""
        if not self.include_market_state:
            return
        # Use the first pair's DataFrame if self.data is a dict
        if isinstance(self.data, dict):
            base_df = next(iter(self.data.values()))
        else:
            base_df = self.data
        # Calculate volatility (rolling standard deviation of returns)
        returns = base_df['close'].pct_change()
        self.volatility = returns.rolling(window=self.volatility_window).std().fillna(0)
        # Calculate trend strength (moving average slope)
        ma_short = base_df['close'].rolling(window=10).mean()
        ma_long = base_df['close'].rolling(window=50).mean()
        self.trend_strength = (ma_short - ma_long) / ma_long
        self.trend_strength = self.trend_strength.fillna(0)
        # Calculate momentum (RSI-like indicator)
        delta = base_df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-8)
        self.momentum = 100 - (100 / (1 + rs))
        self.momentum = self.momentum.fillna(50)
        # Market regime (0=sideways, 1=trending, 2=volatile)
        vol_threshold = self.volatility.quantile(0.7)
        trend_threshold = abs(self.trend_strength).quantile(0.7)
        self.market_regime = np.zeros(len(base_df))
        self.market_regime[self.volatility > vol_threshold] = 2  # Volatile
        self.market_regime[abs(self.trend_strength) > trend_threshold] = 1  # Trending
        logger.info("Calculated market indicators: volatility, trend, momentum, regime")
    
    def reset(self, seed: Optional[int] = None) -> np.ndarray:
        """Reset environment to start new episode"""
        super().reset(seed=seed)
        
        # Reset trading state
        self.current_balance = self.initial_balance
        self.positions = np.zeros(len(FOREX_PAIRS))
        self.equity_curve = [self.initial_balance]
        self.returns_history = []
        self.trades_history = []
        
        # Reset metrics
        self.metrics = TradingMetrics()
        self.metrics.current_equity = 1.0
        self.metrics.peak_equity = 1.0
        
        # Reset reward function state
        self.reward_function.reset_state()
        
        # Choose random start point
        if hasattr(self, 'valid_start_indices') and self.valid_start_indices:
            self.current_step = np.random.choice(self.valid_start_indices)
        else:
            self.current_step = self.lookback_window
        
        # Get initial observation
        observation = self._get_observation()
        
        logger.debug(f"Reset environment: step={self.current_step}, balance={self.current_balance}")
        
        return observation
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Execute one trading step"""
        # Validate action
        action = np.clip(action, -1.0, 1.0)
        
        # Calculate new positions (scaled by max position size)
        new_positions = action * self.max_position_size
        
        # Calculate position changes and transaction costs
        position_changes = new_positions - self.positions
        transaction_costs = np.sum(np.abs(position_changes)) * self.transaction_cost
        
        # Update positions
        old_positions = self.positions.copy()
        self.positions = new_positions
        
        # Get current and next prices for return calculation
        current_prices = self._get_current_prices()
        
        # Move to next step
        self.current_step += 1
        
        # Calculate returns if we have next prices
        if self.current_step < len(self.data):
            next_prices = self._get_current_prices()
            price_changes = (next_prices - current_prices) / current_prices
            
            # Calculate portfolio return
            portfolio_return = np.sum(old_positions * price_changes)
            
            # Apply transaction costs
            portfolio_return -= transaction_costs
            
            # Update balance and equity
            self.current_balance *= (1 + portfolio_return)
            self.equity_curve.append(self.current_balance)
            self.returns_history.append(portfolio_return)
            
            # Calculate reward using custom reward function
            reward_input = torch.tensor(new_positions, dtype=torch.float32).unsqueeze(0)
            price_change_input = torch.tensor(price_changes, dtype=torch.float32).unsqueeze(0)
            reward = self.reward_function(reward_input, price_change_input).item()
            
            # Update metrics
            self._update_metrics(portfolio_return, transaction_costs)
            
        else:
            # End of data
            portfolio_return = 0.0
            reward = 0.0
        
        # Get new observation
        observation = self._get_observation()
        
        # Check termination conditions
        done = self._check_termination()
        
        # Prepare info dict
        info = {
            'portfolio_return': portfolio_return,
            'transaction_costs': transaction_costs,
            'current_balance': self.current_balance,
            'positions': self.positions.copy(),
            'metrics': self.metrics,
            'step': self.current_step
        }
        
        return observation, reward, done, info
    
    def _get_current_prices(self) -> np.ndarray:
        """Get current prices for all forex pairs"""
        if self.current_step >= len(self.data):
            return np.ones(len(FOREX_PAIRS))  # Default prices
        
        # For simplicity, use close price with small variations for different pairs
        base_price = self.data.iloc[self.current_step]['close']
        prices = np.array([base_price * (1 + i * 0.001) for i in range(len(FOREX_PAIRS))])
        
        return prices
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation state"""
        if self.current_step >= len(self.features):
            # Return zero observation if beyond data
            return np.zeros(self.observation_space.shape[0], dtype=np.float32)
        
        # Get current features
        features = self.features[self.current_step].astype(np.float32)
        
        # Portfolio state: positions + balance + equity + drawdown
        equity_ratio = self.current_balance / self.initial_balance
        drawdown = (self.metrics.peak_equity - equity_ratio) / self.metrics.peak_equity
        
        portfolio_state = np.concatenate([
            self.positions,
            [self.current_balance / self.initial_balance],  # Normalized balance
            [equity_ratio],  # Equity ratio
            [drawdown]  # Current drawdown
        ]).astype(np.float32)
        
        # Market state features
        if self.include_market_state and self.current_step < len(self.data):
            market_state = np.array([
                self.volatility.iloc[self.current_step],
                self.trend_strength.iloc[self.current_step],
                self.momentum.iloc[self.current_step] / 100.0,  # Normalize to [0,1]
                self.market_regime[self.current_step] / 2.0  # Normalize to [0,1]
            ]).astype(np.float32)
        else:
            market_state = np.zeros(4 if self.include_market_state else 0, dtype=np.float32)
        
        # Combine all observations
        observation = np.concatenate([features, portfolio_state, market_state])
        
        # Normalize if requested
        if self.normalize_observations:
            observation = self._normalize_observation(observation)
        
        return observation
    
    def _normalize_observation(self, observation: np.ndarray) -> np.ndarray:
        """Normalize observation to reasonable ranges"""
        # Simple normalization - in practice, you'd use running statistics
        return np.tanh(observation / 10.0)  # Soft normalization
    
    def _update_metrics(self, portfolio_return: float, transaction_costs: float):
        """Update performance metrics"""
        # Update equity tracking
        equity_ratio = self.current_balance / self.initial_balance
        self.metrics.current_equity = equity_ratio
        
        if equity_ratio > self.metrics.peak_equity:
            self.metrics.peak_equity = equity_ratio
        
        # Update drawdown
        drawdown = (self.metrics.peak_equity - equity_ratio) / self.metrics.peak_equity
        self.metrics.max_drawdown = max(self.metrics.max_drawdown, drawdown)
        
        # Update returns
        self.metrics.total_return = equity_ratio - 1.0
        
        # Update trading statistics
        if abs(portfolio_return) > 1e-6:  # Significant trade
            self.metrics.total_trades += 1
            self.metrics.total_fees += transaction_costs
            
            if portfolio_return > 0:
                self.metrics.profitable_trades += 1
        
        # Calculate win rate
        if self.metrics.total_trades > 0:
            self.metrics.win_rate = self.metrics.profitable_trades / self.metrics.total_trades
        
        # Calculate Sharpe ratio
        if len(self.returns_history) > 1:
            returns_array = np.array(self.returns_history)
            excess_returns = returns_array - self.risk_free_rate / 252  # Daily risk-free rate
            if np.std(excess_returns) > 0:
                self.metrics.sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def _check_termination(self) -> bool:
        """Check if episode should terminate"""
        # Maximum steps reached
        if self.current_step >= len(self.data) - 1:
            return True
        
        # Maximum episode length
        if len(self.equity_curve) >= self.max_episode_steps:
            return True
        
        # Bankruptcy (balance too low)
        if self.current_balance < self.initial_balance * 0.1:  # 90% loss
            logger.warning(f"Episode terminated due to large loss: {self.current_balance}")
            return True
        
        # Excessive drawdown
        if self.metrics.max_drawdown > 0.5:  # 50% drawdown
            logger.warning(f"Episode terminated due to excessive drawdown: {self.metrics.max_drawdown}")
            return True
        
        return False
    
    def render(self, mode: str = 'human') -> Optional[np.ndarray]:
        """Render environment state"""
        if mode == 'human':
            print(f"Step: {self.current_step}")
            print(f"Balance: ${self.current_balance:.2f}")
            print(f"Equity: {self.metrics.current_equity:.4f}")
            print(f"Drawdown: {self.metrics.max_drawdown:.4f}")
            print(f"Positions: {self.positions}")
            print(f"Sharpe: {self.metrics.sharpe_ratio:.4f}")
            print("-" * 40)
        
        return None
    
    def get_episode_summary(self) -> Dict[str, Any]:
        """Get summary of completed episode"""
        return {
            'total_return': self.metrics.total_return,
            'sharpe_ratio': self.metrics.sharpe_ratio,
            'max_drawdown': self.metrics.max_drawdown,
            'win_rate': self.metrics.win_rate,
            'total_trades': self.metrics.total_trades,
            'total_fees': self.metrics.total_fees,
            'final_balance': self.current_balance,
            'steps': len(self.equity_curve),
            'equity_curve': self.equity_curve.copy()
        }
    
    def set_data(self, data: pd.DataFrame):
        """Set new data for the environment"""
        self.data = data
        self._prepare_data()
        logger.info(f"Updated environment data: {len(data)} timesteps")


def create_forex_environment(data: pd.DataFrame = None, **kwargs) -> ForexTradingEnvironment:
    """
    Factory function to create Forex trading environment
    
    Args:
        data: Historical price data
        **kwargs: Environment configuration
        
    Returns:
        Configured ForexTradingEnvironment
    """
    # Get defaults from config
    env_config = {
        'initial_balance': 10000.0,
        'transaction_cost': 0.0001,
        'max_position_size': 0.1,
        'max_episode_steps': 1000,
        'lookback_window': 100,
        **kwargs
    }
    
    return ForexTradingEnvironment(data=data, **env_config)


def test_environment():
    """Test the trading environment"""
    logger.info("Testing Forex trading environment...")
    
    # Create synthetic data for testing
    np.random.seed(42)
    n_steps = 2000
    
    # Generate realistic price data
    initial_price = 1.0
    returns = np.random.normal(0, 0.01, n_steps)  # 1% daily volatility
    prices = [initial_price]
    
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLCV data
    data = pd.DataFrame({
        'open': prices[:-1],
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices[:-1]],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices[:-1]],
        'close': prices[1:],
        'volume': np.random.randint(1000, 10000, n_steps)
    })
    
    # Create environment
    env = create_forex_environment(data=data, max_episode_steps=100)
    
    # Test episode
    obs = env.reset()
    assert obs.shape == env.observation_space.shape, f"Observation shape mismatch: {obs.shape} vs {env.observation_space.shape}"
    
    total_reward = 0
    for step in range(50):
        # Random action
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        total_reward += reward
        
        if done:
            break
    
    # Get episode summary
    summary = env.get_episode_summary()
    
    logger.info(f"✓ Environment test completed:")
    logger.info(f"  Steps: {step + 1}")
    logger.info(f"  Total reward: {total_reward:.4f}")
    logger.info(f"  Final return: {summary['total_return']:.4f}")
    logger.info(f"  Sharpe ratio: {summary['sharpe_ratio']:.4f}")
    logger.info(f"  Max drawdown: {summary['max_drawdown']:.4f}")
    
    return True


if __name__ == "__main__":
    # Run tests
    test_environment() 