# Clojure Trader

## Overview

Welcome to **Clojure Trader**, an advanced trading framework designed for optimal performance in algorithmic trading. This personal project combines the power of Clojure with modern trading strategies to capitalize on market opportunities.

## Project Objective

The primary objective of this project is to develop, test, and optimize trading algorithms using a data-driven methodology. Leveraging genetic algorithms, the framework searches through a space of trading strategies to identify the most effective ones for various financial instruments.

## Key Features

- **Intuitive Strategy Definition**: Define strategies using simple vectors of positive integers representing buy and sell signals, making it easy to create custom algorithms.
- **Genetic Algorithm**: Employ genetic algorithm techniques for strategy backtesting optimization.
- **Multi-Instrument Support**: Analyze and optimize trading strategies across multiple forex pairs and cryptocurrencies.
- **Asynchronous Processing**: Efficiently manage data retrieval and processing through asynchronous operations.
- **Extensive Library Support**: Utilize a range of libraries for data manipulation, visualization, and HTTP requests.

## Technologies and Dependencies

- **Clojure**: A modern Lisp dialect for robust and efficient programming.
- **CUDA**: For parallel processing of vector computations to enhance backtest performance.
- **Compojure**: Simplifies routing and handling requests.
- **Midje**: Provides a framework for testing and validation.
- **metasoarous/oz**: For data visualizations.
- **org.clojure/data.csv**: For CSV handling.
- **clj-http/clj-http**: For making HTTP requests.

## Roadmap

Plan to extend Clojure Trader with further enhancements:

- Implement web UI
  - Visualize performance
  - Manage portfolios
  - Control trading parameters
- Integration with additional trading APIs such as Interactive Brokers and others.
- Experiment with position entering and exiting time based strategies.

## Getting Started

### Prerequisites

Make sure you have the following installed:

- Java (JDK 8 or later)
- Clojure
- VSCode with Calva extension

### Installation

Clone the repository:

```bash
git clone https://github.com/vandyand/clojure-trader.git
cd clojure-trader
code .
```

Update environment variables in `.sensitive.json`:

```json
{
  "OANDA_DEMO_KEY": "xxxxxxxx",
  "OANDA_LIVE_KEY": "xxxxxxxx",
  "BINANCE_API_KEY": "xxxxxxxx",
  "BINANCE_API_SECRET": "xxxxxxxx"
}
```

Update account information in `.env.json`:

```json
{
  "OANDA_LIVE_ACCOUNT_ID": "xxxxxxxx",
  "OANDA_DEMO_ACCOUNT_ID": "xxxxxxxx"
}
```

Start the Python server if using cryptocurrency trading:

```bash
./python-binance-wrapper/startup.sh
```

Install dependencies:
From VSCode Command Pallette:

```
Calva: Start a Project REPL and Connect (aka Jack-in)
```

Run the application:  
From the calva repl run src/portfolio.clj file. This will run backtests on the top 20 most liquid forex pairs and cryptocurrencies, calculate optimal position sizes and post orders to OANDA and Binance.

## Contribution

Contributions are welcome! Please submit pull requests or open issues to discuss improvements.

## License

This project is licensed under the MIT License.

# RL Trading System - ETF Integration Fixes

This document outlines fixes implemented to resolve issues in the reinforcement learning trading system, particularly around ETF data integration and tensor shape mismatches.

## Issues Fixed

### 1. Tensor Shape Mismatch Error

**Problem:** The error message `mat1 and mat2 shapes cannot be multiplied (1x2940 and 1084x256)` indicated a mismatch between the feature vector size during inference (2940) and the size expected by the model (1084).

**Solution:** We implemented adaptive resizing in the `prepare_feature_vector` method in `rl/data_fetcher.py` to ensure the feature vector always matches the expected model input dimension:

- If the feature vector is too long, it's truncated
- If it's too short, it's padded with zeros
- Detailed logging was added to track the transformation

### 2. NaN Value Handling in ETF Data Processing

**Problem:** The pandas_ta library was failing with NaN values when processing ETF data, causing feature generation to fail.

**Solution:** We improved NaN handling throughout the ETF data pipeline:

- Enhanced `generate_features` function in `rl/data/generate_etf_features.py` with robust NaN detection and handling
- Added try/except blocks to continue processing even if some indicators fail
- Improved JSON serialization to handle NaN and infinite values properly

### 3. ETF Data Fetching Robustness

**Problem:** yfinance API calls sometimes failed due to network issues or returned incomplete data.

**Solution:** Added retry logic in `fetch_historical_etf_data` with better error handling:

- Implemented automatic retries for temporary network issues
- Added validation of returned data quality
- Improved NaN detection and handling in returned data

## How to Run the System

Use the new `--help-etf` flag to get help on ETF integration:

```bash
python run_trading_system.py --help-etf
```

To run the system with ETF support:

```bash
# Run once with ETF data refresh (recommended for testing)
python run_trading_system.py --single-run --refresh-etf --dry-run

# Run continuously with advanced features
python run_trading_system.py --refresh-etf --use-regime-detection --adapt-position-sizing --interval 60
```

## Required Dependencies

Make sure you have all dependencies installed:

```bash
pip install yfinance pandas_ta numpy pandas torch psycopg2 scikit-learn
```

## Troubleshooting

If you still encounter issues:

1. Check the logs in the `logs/` directory for specific error messages
2. Try running the ETF data ingestion separately to debug any issues:
   ```bash
   python rl/data/etf_data_ingestion.py --symbols SPY QQQ --period 1y --generate-features
   ```
3. Make sure your model file exists at the specified path

## Future Improvements

Future work could include:

- Retraining the model with the exact feature set available during inference
- Implementing more ETF-specific features
- Adding better visualization of feature contributions
- Further optimizing the feature set to reduce dimensionality
