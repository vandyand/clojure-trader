# Top 20 most liquid crypto perpetual futures pairs on Bitunix (USDT-denominated)
# Based on CoinMarketCap top market cap instruments - these are the pairs that will be traded with long/short positions
CRYPTO_FUTURES_PAIRS = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT",
    "DOGEUSDT", "ADAUSDT", "TRXUSDT", "ATOMUSDT", "ZECUSDT",
    "LINKUSDT", "AVAXUSDT", "XLMUSDT", "BCHUSDT", "ICPUSDT",
    "FILUSDT", "DOTUSDT", "LTCUSDT", "MATICUSDT", "UNIUSDT"
]

# List of 34 ETF symbols used for market correlation (same as other systems)
ETF_SYMBOLS = [
    "ASHR", "BND", "BTC-USD", "BWX", "CEW",
    "XLV", "DBA", "DBC", "DIA", "EEM",
    "EFA", "EMB", "EWJ", "EWZ", "EZU",
    "FXB", "FXE", "FXF", "FXY", "GLD",
    "IEF", "QQQ", "SHY", "SLV", "SPY",
    "TLT", "UNG", "USO", "UUP", "VIXY",
    "VNQ", "XLE", "XLF", "XLI"
]

# Fibonacci sequence periods for feature engineering
# 15 periods: [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
FIBONACCI_PERIODS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# Feature engineering configuration
N_CRYPTO_PAIRS = len(CRYPTO_FUTURES_PAIRS)  # 20
N_ETF_SYMBOLS = len(ETF_SYMBOLS)  # 34
N_FIBONACCI_PERIODS = len(FIBONACCI_PERIODS)  # 15

# Fibonacci features: 20 pairs × 15 periods = 300 features
FIBONACCI_FEATURES = N_CRYPTO_PAIRS * N_FIBONACCI_PERIODS  # 300

# ETF features: 34 ETFs × 23 technical indicators = 782 features
ETF_FEATURES_PER_SYMBOL = 23
ETF_TOTAL_FEATURES = N_ETF_SYMBOLS * ETF_FEATURES_PER_SYMBOL  # 782

# Total input features: 300 (Fibonacci) + 782 (ETF) + 160 (crypto technical) = 1,242
CRYPTO_TECHNICAL_FEATURES = N_CRYPTO_PAIRS * 8  # 8 technical indicators per crypto pair
TOTAL_INPUT_FEATURES = FIBONACCI_FEATURES + ETF_TOTAL_FEATURES + CRYPTO_TECHNICAL_FEATURES  # 1,242

# Autoencoder bottleneck dimension
AUTOENCODER_BOTTLENECK_DIM = 149

# Trading configuration
ACCOUNT_SIZE = 480.0  # USD
RISK_TOLERANCE_PERCENT = 5.0  # 5% risk tolerance
MAX_LEVERAGE = 125.0  # Maximum leverage available
TRANSACTION_COST_RATE = 0.001  # 0.1% per trade (higher than forex due to crypto volatility)

# Reward function parameters
DSR_BETA = 0.95  # Differential Sharpe Ratio decay rate
ENTROPY_SCALING = True  # Enable entropy penalty for position diversification
CONFIDENCE_WEIGHTING = True  # Enable confidence weighting based on Dirichlet concentration

# Training parameters
BATCH_SIZE = 256  # Increased for better GPU utilization and faster training
LEARNING_RATE_ACTOR = 3e-4  # Increased for faster learning
LEARNING_RATE_CRITIC = 1e-3  # Keep critic rate stable
GAMMA = 0.99  # Discount factor
ENTROPY_WEIGHT = 0.001  # Further reduced to allow more exploitation

# Risk management
MAX_POSITION_SIZE = 0.2  # Maximum 20% of portfolio in single position
MAX_DRAWDOWN = 0.15  # Maximum 15% drawdown
VOLATILITY_LOOKBACK = 20  # Days for volatility calculation
TREND_LOOKBACK = 50  # Days for trend strength calculation 