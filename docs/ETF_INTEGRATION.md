# ETF Data Integration for Reinforcement Learning Trading System

This document outlines the integration of ETF (Exchange-Traded Fund) data into the RL trading system using the yfinance library as the primary data source.

## Components Added/Modified

1. **ETF Data Fetcher (`rl/data/fetch_etf_data.py`)**

   - Implements a robust fetching mechanism for ETF data
   - Includes caching to minimize API calls
   - Provides functions for both historical and latest price data

2. **ETF Data Ingestion (`rl/data/etf_data_ingestion.py`)**

   - Ingests ETF data from yfinance into the database
   - Handles data standardization and database interactions
   - Generates and stores features for analysis

3. **Data Fetcher Enhancement (`rl/data_fetcher.py`)**

   - Updated to handle both forex and ETF data
   - Intelligently selects appropriate data source based on instrument type
   - Unified feature calculation for all instrument types

4. **Trading System Integration (`run_trading_system.py`)**
   - Added ETF data refresh capability
   - Enhanced position submission to handle ETF positions
   - Improved logging with instrument type identification

## Setup Requirements

1. **Dependencies**

   - Added yfinance to requirements.txt
   - Install with: `pip install -r rl/requirements.txt`

2. **Database Configuration**

   - Ensure PostgreSQL database is accessible with credentials in environment variables:
     - DB_NAME (default: rl_forex)
     - DB_USER (default: postgres)
     - DB_PASSWORD (default: password)
     - DB_HOST (default: localhost)
     - DB_PORT (default: 5432)

3. **OANDA API Configuration**
   - Existing environment variables are still required for forex trading:
     - OANDA_LIVE_KEY
     - OANDA_DEMO_KEY
     - OANDA_LIVE_URL
     - OANDA_DEMO_URL
     - OANDA_LIVE_ACCOUNT_ID
     - OANDA_DEMO_ACCOUNT_ID
     - USE_LIVE (default: false)

## Usage Instructions

### Fetching ETF Data Manually

To refresh ETF data separately from the trading system:

```bash
# Fetch data for specific ETFs
python rl/data/etf_data_ingestion.py --symbols SPY QQQ IWM GLD --period 5y

# Auto-detect ETFs from database and generate features after ingestion
python rl/data/etf_data_ingestion.py --generate-features

# Only regenerate features for existing data
python rl/data/etf_data_ingestion.py --features-only
```

### Running the Trading System with ETF Support

```bash
# Run once with ETF data refresh and place orders in dry-run mode
python run_trading_system.py --single-run --refresh-etf --dry-run

# Run continuously with adaptive position sizing and regime detection
python run_trading_system.py --refresh-etf --use-regime-detection --adapt-position-sizing --interval 60
```

### Command-line Options

The trading system has new options:

- `--refresh-etf`: Refresh ETF data before each trading cycle
- `--account-size`: Specify account size in USD (default: 1000.0)
- `--risk-percent`: Maximum percentage of account to risk (default: 5.0)
- `--interval`: Minutes between trading cycles when running continuously (default: 60)
- `--dry-run`: Run in dry-run mode (no real orders)
- `--single-run`: Run once and exit
- `--use-regime-detection`: Use market regime detection
- `--adapt-position-sizing`: Use adaptive position sizing based on regimes

## Implementation Details

### ETF Data Flow

1. yfinance API → fetch_etf_data.py → Local cache (for performance)
2. fetch_etf_data.py → etf_data_ingestion.py → PostgreSQL (etf_raw table)
3. etf_raw table → feature generation → etf_features table
4. data_fetcher.py → RL model → Position sizing → OANDA/ETF broker

### Database Schema

**etf_raw Table**

- timestamp (TIMESTAMP WITH TIME ZONE)
- instrument (TEXT)
- granularity (TEXT)
- open (DOUBLE PRECISION)
- high (DOUBLE PRECISION)
- low (DOUBLE PRECISION)
- close (DOUBLE PRECISION)
- volume (DOUBLE PRECISION)

**etf_features Table**

- timestamp (TIMESTAMP WITH TIME ZONE)
- instrument (TEXT)
- granularity (TEXT)
- features (JSONB)

## Limitations and Future Enhancements

1. **ETF Broker Integration**

   - Currently, ETF positions are calculated but not sent to an actual broker
   - Future enhancement: Add integration with a stock/ETF broker API like Alpaca or Interactive Brokers

2. **Intraday Data**

   - Current implementation focuses on daily data
   - Future enhancement: Support for higher-frequency data for intraday trading

3. **ETF-Specific Features**

   - Current features are similar to those used for forex
   - Future enhancement: Add ETF-specific features like sector analysis, fund flows, etc.

4. **Symbol Selection**
   - Future enhancement: Implement dynamic ETF selection based on performance metrics

## Troubleshooting

- **yfinance API Issues**: If you encounter rate limiting or connection issues with yfinance, increase the cache TTL in fetch_etf_data.py
- **Database Connection Problems**: Verify PostgreSQL is running and credentials are correct in environment variables
- **Missing ETF Data**: Check the logs for specific error messages. Some symbols may not be available in yfinance.
