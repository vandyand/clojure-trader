# Clojure Trader

A trading system built with Clojure that automatically manages forex and cryptocurrency positions.

## Project Structure

- `frontend/` - React dashboard for visualizing trades and portfolio
- `src/` - Clojure backend code for trading algorithms and API connections
- `src/portfolio.clj` - The portfolio management script that updates positions

## Setup

### Prerequisites

- Java 17+
- Clojure
- Node.js 18+ (for frontend)
- OANDA account (for forex trading)
- Binance account (for crypto trading)

### Configuration

1. Copy `.env.example` to `.env.json` and fill in your details
2. Copy `.sensitive.example` to `.sensitive.json` and add your API keys

## Local Development

### Backend

```
clj -m nean.server
```

### Frontend

```
cd frontend
npm install
npm start
```

## Deployment

### Heroku Deployment

1. Create a Heroku app for the backend:

```
heroku create clojure-trader-backend
```

2. Set environment variables:

```
heroku config:set OANDA_LIVE_OR_DEMO=DEMO
heroku config:set OANDA_DEMO_ACCOUNT_ID=your-account-id
heroku config:set OANDA_DEMO_KEY=your-api-key
```

3. Push to Heroku:

```
git push heroku master
```

## Scheduling Portfolio Updates

### Option 1: Heroku Scheduler

1. Install the Heroku Scheduler add-on:

```
heroku addons:create scheduler:standard
```

2. Create a scheduled job to run daily at your preferred time (e.g., 6-7 PM EST):

```
clj run-portfolio.clj
```

### Option 2: GitHub Actions

1. Add a GitHub workflow file to run the portfolio script daily:

```yaml
name: Daily Portfolio Update

on:
  schedule:
    # Run at 6:30 PM Eastern Time (22:30 UTC)
    - cron: "30 22 * * *"

jobs:
  update-portfolio:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          distribution: "temurin"
          java-version: "17"
      - uses: DeLaGuardo/setup-clojure@12.1
        with:
          cli: 1.11.1.1273
      - name: Run Portfolio Update
        run: clj -M run-portfolio.clj
        env:
          OANDA_LIVE_OR_DEMO: ${{ secrets.OANDA_LIVE_OR_DEMO }}
          OANDA_DEMO_ACCOUNT_ID: ${{ secrets.OANDA_DEMO_ACCOUNT_ID }}
          OANDA_LIVE_ACCOUNT_ID: ${{ secrets.OANDA_LIVE_ACCOUNT_ID }}
          OANDA_DEMO_KEY: ${{ secrets.OANDA_DEMO_KEY }}
          OANDA_LIVE_KEY: ${{ secrets.OANDA_LIVE_KEY }}
          BINANCE_API_KEY: ${{ secrets.BINANCE_API_KEY }}
          BINANCE_SECRET_KEY: ${{ secrets.BINANCE_SECRET_KEY }}
```

### Option 3: Local Crontab (Unix/Linux/macOS)

Add a crontab entry to run the script daily at 6:30 PM Eastern:

```
30 18 * * * cd /path/to/clojure-trader && clj -M run-portfolio.clj >> portfolio.log 2>&1
```

## Architecture

The system consists of:

1. **Portfolio Management** - Analyzes market conditions and determines position sizes
2. **Backend API** - Provides data to the frontend and executes trades
3. **Frontend Dashboard** - Visualizes trading results and portfolio performance

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
