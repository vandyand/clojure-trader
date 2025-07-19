# OANDA Position Size Calculation in Python

This document explains the OANDA position sizing implementation that matches the Clojure code's logic.

## Problem

The Python implementation for syncing positions with OANDA was inconsistent with the Clojure code's position sizing logic, causing the following issues:

1. Position sizes for certain instruments were incorrect (notably EUR_USD)
2. The web UI in OANDA showed different position sizes than the Python code was targeting

## Solution

We've implemented a Python-based position sizing module that follows the same logic as the Clojure implementation. The key components:

### 1. Core Position Sizing Logic

The function `get_target_position_amount` in `position_sizing.py` implements the same logic as the Clojure `get-target-position-amount` function in `portfolio.clj`. This handles different currency pairs correctly, including:

- USD-base pairs (USD_JPY, USD_CAD, etc.)
- USD-quote pairs (EUR_USD, GBP_USD, etc.)
- Cross pairs (EUR_GBP, GBP_JPY, etc.)

### 2. Forex Position Multiplier

The Clojure code applies a 25x multiplier to forex positions. This is now implemented in the Python code via the `apply_forex_multiplier` function.

### 3. Position Difference Calculation

Instead of closing and reopening positions, we calculate the difference between current and target positions and only execute orders for the difference. This:

- Reduces unnecessary slippage
- Preserves existing positions when possible
- Makes position syncing more efficient

## Key Files

- `rl/position_sizing.py`: Core position sizing logic that matches the Clojure implementation
- `rl/sync_positions.py`: Updated to use the correct position sizing logic
- `compare_positions.py`: Utility to verify position sizes between current OANDA positions and expected values

## Usage

To sync positions from terminal output with OANDA:

```
python rl/sync_positions.py
```

To check current positions against expected positions:

```
python compare_positions.py
```

## Implementation Details

### Position Sizing Logic

The position sizing logic handles different types of currency pairs:

```python
# For pairs ending in USD (like EUR_USD)
if instrument_ends_in_usd_or_usdt(instrument):
    return usd_amount / latest_price

# For USD-based pairs (like USD_JPY)
elif instrument_has_usd_in_it(instrument):
    if instrument_ends_in_jpy(instrument):
        return usd_amount * latest_price * 0.01
    else:
        return usd_amount * latest_price

# For pairs ending in JPY (like EUR_JPY)
elif instrument_ends_in_jpy(instrument):
    usd_jpy_price = get_latest_price("USD_JPY")
    return (usd_amount * latest_price) / usd_jpy_price

# Similar logic for other currency crosses...
```

### Position Difference Calculation

```python
def calculate_position_changes(current_positions, target_positions):
    """
    Instead of closing and reopening positions, calculate only the changes needed
    """
    changes = []

    # For each instrument, calculate the difference between current and target
    for instrument, current_units in current_positions.items():
        target_units = target_position_map.get(instrument, 0)
        delta_units = target_units - current_units

        if delta_units != 0:
            changes.append({
                "instrument": instrument,
                "units": delta_units
            })

    # Add new positions
    for instrument, target_units in target_position_map.items():
        if instrument not in current_positions and target_units != 0:
            changes.append({
                "instrument": instrument,
                "units": target_units
            })

    return changes
```

## Verification

The `compare_positions.py` script verifies that our Python implementation produces the same position sizes as expected. It:

1. Retrieves current positions from OANDA
2. Compares them with expected positions from our hardcoded list
3. Shows any discrepancies in direction or unit size

After implementing our position sizing fixes, all positions match correctly between OANDA and our expected values.
