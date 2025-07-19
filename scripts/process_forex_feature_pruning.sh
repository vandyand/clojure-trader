#!/bin/bash

# Process remaining forex instruments for feature pruning
# We've already processed EUR_USD and USD_JPY

INSTRUMENTS=(
  "GBP_USD"
  "AUD_USD"
  "USD_CHF"
  "USD_CAD"
  "NZD_USD"
  "EUR_JPY"
  "GBP_JPY"
  "EUR_GBP"
  "EUR_CHF"
  "EUR_AUD"
  "EUR_CAD"
  "GBP_CHF"
  "AUD_JPY"
  "AUD_CHF"
  "CAD_JPY"
  "NZD_JPY"
  "GBP_AUD"
  "AUD_NZD"
)

for instrument in "${INSTRUMENTS[@]}"; do
  echo "Processing feature pruning for $instrument..."
  python rl/data/feature_pruning.py --instrument "$instrument" --n_features 23
  echo "Completed $instrument"
  echo "------------------------------"
done

echo "All forex instruments processed!" 