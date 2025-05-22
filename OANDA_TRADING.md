# OANDA Trading Integration

This document explains how to use the OANDA trading integration for the reinforcement learning trading system.

## Prerequisites

1. An OANDA demo or live account
2. OANDA API token
3. Python 3.6+ with oandapyV20 installed

## Setup

1. Install the OANDA API Python package:

   ```bash
   pip install oandapyV20
   ```

2. Set up your OANDA credentials:

   ```bash
   # Option 1: Set environment variables
   export OANDA_ACCOUNT_ID="your_account_id_here"
   export OANDA_API_KEY="your_api_key_here"

   # Option 2: Add to your shell profile (.bashrc, .zshrc, etc.)
   echo 'export OANDA_ACCOUNT_ID="your_account_id_here"' >> ~/.zshrc
   echo 'export OANDA_API_KEY="your_api_key_here"' >> ~/.zshrc
   source ~/.zshrc
   ```

## Scripts

### 1. Sync Positions Script

The `rl/sync_positions.py` script synchronizes your OANDA account with the trading signals from the RL model.

```bash
# Run a dry run (doesn't place trades, just creates signal file)
python rl/sync_positions.py --dry-run

# Place trades using environment variables for credentials
python rl/sync_positions.py

# Place trades with explicit credentials
python rl/sync_positions.py --account-id "your_account_id" --api-token "your_api_key"

# Close existing positions before placing new ones
python rl/sync_positions.py --close-existing
```

### 2. OANDA Trader Library

The `rl/oanda_trader.py` script provides a Python library for interacting with the OANDA API. You can use it programmatically or directly:

```bash
# Verify account connection
python rl/oanda_trader.py --verify-only

# Close all existing positions
python rl/oanda_trader.py --close-positions

# Execute trades based on a specific signal file
python rl/oanda_trader.py --signal-file signals/your_signal_file.json
```

## Trading Signals Format

The trading signals are stored in JSON files in the `signals/` directory. The format is:

```json
{
  "account_size": 1000.0,
  "risk_amount": 50.0,
  "positions": [
    {
      "instrument": "EUR_USD",
      "direction": "SHORT",
      "position_size": 6.896073,
      "usd_amount": 0.31
    },
    {
      "instrument": "USD_JPY",
      "direction": "LONG",
      "position_size": 15.530363,
      "usd_amount": 0.43
    }
    // ... more positions
  ]
}
```

## Position Sizing

The script automatically adjusts the position sizes to suitable values for OANDA:

1. Very small positions (<1.0) use the minimum trade size (1000 units)
2. Larger positions are scaled by 1000 to represent standard lots
3. Short positions have negative units

## Workflow

Typical workflow for using this system:

1. Run the RL trading system to generate signals

   ```bash
   python rl/integrated_trader.py
   ```

2. Examine the generated signals

   ```bash
   cat signals/latest_signal_file.json
   ```

3. Sync your OANDA account with the signals

   ```bash
   python rl/sync_positions.py
   ```

4. Verify the positions in your OANDA dashboard

## Troubleshooting

- **ImportError: oandapyV20 not installed**: Run `pip install oandapyV20`
- **No OANDA account ID provided**: Set the OANDA_ACCOUNT_ID environment variable
- **No OANDA API token provided**: Set the OANDA_API_KEY environment variable
- **Failed to connect to OANDA account**: Verify your account ID and API token
