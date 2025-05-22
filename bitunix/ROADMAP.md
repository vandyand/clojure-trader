# Bitunix API Integration Roadmap

This document outlines the development tasks required to implement the Bitunix API integration.

## Phase 1: Core Functionality & Setup

- [x] **Environment Setup:**
  - [x] Initialize Python project (e.g., using Poetry or venv).
  - [x] Install necessary libraries (e.g., `requests`, `python-dotenv`).
  - [x] Create a `.gitignore` file.
- [x] **API Client Base:**
  - [x] Implement a base class for API requests (handling authentication, headers, base URL).
  - [ ] Add error handling and response parsing.
- [x] **Configuration Management:**
  - [x] Securely load API keys (`BITUNIX_API_KEY`, `BITUNIX_SECRET_KEY`) from environment variables.

## Phase 2: Candlestick Data

- [x] **Endpoint Implementation:**
  - [x] Identify and implement the Bitunix API endpoint for fetching historical candlestick data.
  - [x] Define data structures/classes for candlestick data.
- [x] **Parameterization:**
  - [x] Allow specifying symbol (e.g., BTCUSDT), interval (e.g., 1m, 1h, 1d), start time, end time, and limit.
- [x] **Data Parsing & Validation:**
  - [x] Parse the API response into a usable format (e.g., list of candlestick objects or pandas DataFrame).
  - [x] Validate the received data.
- [x] **Testing:**
  - [x] Write unit tests for candlestick data retrieval.

## Phase 3: Account Information

- [x] **Endpoint Implementation:**
  - [x] Identify and implement Bitunix API endpoints for fetching account balances.
  - [x] Identify and implement Bitunix API endpoints for fetching current open positions.
  - [x] Define data structures/classes for account balance and position information.
- [ ] **Data Parsing & Validation:**
  - [x] Parse API responses into usable formats.
  - [ ] Validate the received data.
- [ ] **Testing:**
  - [ ] Write unit tests for account information retrieval.

## Phase 4: Order Management

- [ ] **Endpoint Implementation (Order Placement):**
  - [ ] Identify and implement the Bitunix API endpoint for placing new orders (e.g., market, limit).
  - [ ] Define data structures/classes for order parameters and responses.
- [ ] **Endpoint Implementation (Order Modification/Cancellation):**
  - [ ] Identify and implement Bitunix API endpoints for modifying existing orders.
  - [ ] Identify and implement Bitunix API endpoints for cancelling existing orders.
- [ ] **Parameterization:**
  - [ ] Support different order types, symbols, quantities, prices (for limit orders), etc.
- [ ] **Response Handling:**
  - [ ] Process API responses for order placement, modification, and cancellation (success/failure, order IDs).
- [ ] **Testing:**
  - [ ] Write unit tests for placing, modifying, and cancelling orders (consider using a testnet or mock server if available).

## Phase 5: Integration & Refinement

- [ ] **Example Usage Scripts:**
  - [ ] Create example scripts demonstrating how to use each feature of the API client.
- [ ] **Documentation:**
  - [ ] Add docstrings to all functions and classes.
  - [ ] Update `README.md` with usage examples and any new information.
- [ ] **Rate Limiting & Error Handling:**
  - [ ] Implement robust handling for API rate limits.
  - [ ] Enhance global error handling and logging.
- [ ] **Code Review & Refactoring:**
  - [ ] Review the entire codebase for clarity, efficiency, and adherence to best practices.
  - [ ] Refactor as needed.

## Phase 6: Advanced Features (Optional)

- [ ] **WebSocket Integration:**
  - [ ] Explore and implement WebSocket streams for real-time data (e.g., order book updates, live trades).
- [ ] **Advanced Order Types:**
  - [ ] Support for stop-loss, take-profit, and other advanced order types if offered by Bitunix.
- [ ] **Portfolio Tracking:**
  - [ ] Implement higher-level functions for portfolio value calculation and performance tracking.
