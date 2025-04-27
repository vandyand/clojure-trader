# RL Data Pipeline for OANDA Forex

This project provides a robust, extensible data pipeline for reinforcement learning (RL) algorithmic trading on OANDA forex pairs. It fetches historical candlestick data for the most liquid forex pairs, calculates technical indicators, and stores everything in a PostgreSQL/TimescaleDB timeseries database.

## Features

- Fetches historical OHLCV data for top forex pairs (see `constants.py`)
- Calculates technical indicators (e.g., SMA, RSI, MACD) with easy extensibility
- Stores all data in a timeseries-optimized PostgreSQL database (TimescaleDB)
- Designed for RL workflows: all features are normalized using a learned scale/bias + tanh method (per-feature)
- Modular, research-friendly Python codebase

## Directory Structure

- `db/` — Database schema, models, and migrations
- `data/` — Data fetching, indicator calculation, and ingestion
- `notebooks/` — Exploratory analysis and prototyping
- `main.py` — Entry point for data pipeline

## Requirements

- Python 3.8+
- PostgreSQL with TimescaleDB extension
- See `requirements.txt` for Python dependencies

## Extending

- Add new indicators in `data/indicators.py`
- Add new columns to the DB via migration
- Update ingestion logic to compute/store new indicators

## Normalization

All features for the RL autoencoder are normalized using a learned scale and bias (per-feature), followed by a tanh nonlinearity. This is implemented in the model pipeline, not the DB.

---

This project is a foundation for advanced RL-based trading research and production systems.
