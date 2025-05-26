# config/forex_pairs.py

# 20 major forex pairs for trading
FOREX_PAIRS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CHF",
    "USD_CAD", "NZD_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP",
    "EUR_CHF", "EUR_AUD", "EUR_CAD", "GBP_CHF", "AUD_JPY",
    "AUD_CHF", "CAD_JPY", "NZD_JPY", "GBP_AUD", "AUD_NZD"
]

# Extended Fibonacci sequence with 15 numbers for lookback periods
FIBONACCI_PERIODS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# Total input features: 20 pairs × 15 periods = 300 features
TOTAL_INPUT_FEATURES = len(FOREX_PAIRS) * len(FIBONACCI_PERIODS)

# Validate the configuration
assert TOTAL_INPUT_FEATURES == 300, f"Expected 300 features, got {TOTAL_INPUT_FEATURES}" 