# Clojure Trader Frontend

A React-based trading dashboard for Clojure Trader.

## Setup

1. Install dependencies:

   ```
   npm install
   ```

2. Set up environment variables:

   - Copy `.env` to `.env.local`
   - Replace the placeholder OANDA API key with your actual API key

   ```
   REACT_APP_OANDA_API_KEY=your_oanda_api_key_here
   ```

3. Start the development server:
   ```
   npm start
   ```

## API Integration

The app can switch between mock data and real OANDA API data:

### Mock Data

- Default setting for development
- Provides consistent test data for UI development
- No API key required

### OANDA API

- Real-time trading data from OANDA
- Requires an OANDA API key
- Set your API key in `.env.local`
- Switch to OANDA data using the "Data Source" toggle in the header

## Getting an OANDA API Key

1. Sign up for an OANDA demo account at [https://www.oanda.com/demo-account/](https://www.oanda.com/demo-account/)
2. Login to your account
3. Navigate to "My Account" > "Manage API Access"
4. Generate a new API key
5. Add the API key to your `.env.local` file

## Features

- Dashboard with account overview
- Position management
- Performance tracking
- Backtesting tools

## Tech Stack

- React
- TypeScript
- Tailwind CSS
- React Query
- Recharts
- Axios
