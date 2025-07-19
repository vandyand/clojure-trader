# OANDA Position Sizing Documentation

## Overview

This document explains the position sizing mechanism for the OANDA trading system used in our Clojure-Trader application. It describes how position sizes are calculated, how to sync positions with the OANDA platform, and how to verify that positions match our intended allocations.

## Position Sizing Mechanism

### Key Concept

The system uses a simple approach for position sizing:

1. Each trading signal includes a `position_size` value
2. To determine the actual number of units to trade, we simply **round the position_size to the nearest integer**
3. The direction (LONG/SHORT) determines whether this value is positive or negative

### Example

```
For EUR_USD with position_size of 6.896073 and direction SHORT:
- Round 6.896073 to nearest integer = 7
- Apply direction (SHORT) = -7 units
```

## Position Syncing Process

The position syncing workflow uses two primary scripts:

### 1. sync_positions.py

This script:

- Reads target positions (hardcoded or from a file)
- Gets current positions from OANDA
- Calculates necessary changes to bring current positions in line with targets
- Executes only the trades needed to achieve the target positions

To run:

```bash
python rl/sync_positions.py
```

Optional flags:

- `--dry-run`: Show changes without executing them
- `--verify-only`: Only verify account connection
- `--show-reference`: Display reference table for USD-to-units conversion

### 2. compare_positions.py

This script:

- Retrieves current positions from OANDA
- Compares them against expected positions
- Reports matches and mismatches for both direction and unit count

To run:

```bash
python compare_positions.py
```

## Implementation Details

The position sizing calculation happens in two key locations:

1. In `sync_positions.py`:

```python
# Simply round the position_size to get target units
target_units = round(position_size)

# Apply direction
if direction == "SHORT":
    target_units = -abs(target_units)
else:  # LONG
    target_units = abs(target_units)
```

2. In `compare_positions.py`:

```python
# Round to nearest integer
target_units = round(position_size)

if direction == "SHORT":
    target_units = -target_units
```

## Troubleshooting

### Common Issues

1. **Mismatched positions**: If compare_positions.py shows mismatches, run sync_positions.py again to realign positions

2. **Position size discrepancies**: Remember that:

   - Units are always whole numbers (OANDA requirement)
   - Direction determines sign (positive for LONG, negative for SHORT)

3. **Environment variables**: Ensure these are set:
   - `OANDA_DEMO_ACCOUNT_ID`
   - `OANDA_DEMO_KEY`

## Notes for Future Development

1. **Keep it simple**: The current approach of rounding position_size values to integers is intentionally simple and works well

2. **Avoid complicated USD calculations**: The system previously had complex USD-based calculations that led to confusion. The current direct rounding approach is cleaner and more maintainable

3. **Position sizing and risk management**: Remember that position_size values are determined upstream in the trading logic. This system simply converts those values to OANDA-compatible units

## Legacy Approaches (For Reference Only)

Previously, the system attempted more complex position sizing methods:

- Using a 25x forex multiplier
- Implementing USD-based position sizing calculations
- Complex cross-currency conversions

These were found to overcomplicate the system and have been replaced by the simpler rounding method.
