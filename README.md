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
