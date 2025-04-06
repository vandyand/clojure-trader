# Clojure Trader

A modern trading platform built with Clojure, React, and PostgreSQL. This application provides algorithmic trading capabilities with backtesting and live trading features.

## Table of Contents

- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Deployment](#deployment)
- [Database Migration](#database-migration)
- [Authentication](#authentication)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Architecture

The application consists of two main components:

1. **Backend**: A Clojure-based API server with the following features:

   - Trading algorithm implementation
   - Backtesting engine
   - JWT authentication
   - Database integration with PostgreSQL
   - Real-time market data processing

2. **Frontend**: A React application with:
   - Interactive trading dashboard
   - Portfolio analytics
   - Backtesting interface
   - Position management

## Getting Started

### Prerequisites

- JDK 11+
- Leiningen (Clojure build tool)
- Node.js 16+ and npm
- PostgreSQL 12+

### Clone the Repository

```bash
git clone https://github.com/yourusername/clojure-trader.git
cd clojure-trader
```

## Backend Setup

1. Install dependencies:

```bash
./lein deps
```

2. Configure the database:

Create a `.env` file with your database credentials or use environment variables:

```
DATABASE_URL=postgres://username:password@localhost:5432/clojure_trader
JWT_SECRET=your_secret_key_here
```

3. Run the backend server locally:

```bash
./lein run
```

The server will be available at http://localhost:8080

## Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Configure the environment:

Create a `.env` file with your API configuration:

```
REACT_APP_CLOJURE_API_URL=http://localhost:8080
REACT_APP_DEFAULT_API_SOURCE=clojure
```

4. Start the development server:

```bash
npm start
```

The frontend will be available at http://localhost:3000

## Deployment

### Backend Deployment (Heroku)

1. Create a Heroku app:

```bash
heroku create your-app-name
```

2. Add PostgreSQL:

```bash
./heroku-postgres-setup.sh
```

3. Deploy the application:

```bash
./deploy-to-heroku.sh
```

### Frontend Deployment

The frontend can be deployed to various static hosting services:

```bash
cd frontend
./deploy-frontend.sh
```

Follow the interactive prompts to select your preferred hosting platform (GitHub Pages, Netlify, Vercel, etc.).

## Database Migration

The application uses a custom database migration system:

```bash
./lein run -m migrations.core
```

Migrations are automatically run during application startup to ensure the database schema is up-to-date.

## Authentication

The system uses JWT for authentication:

1. Register a user:

```
POST /api/auth/register
{
  "username": "your_username",
  "password": "your_password",
  "email": "your_email@example.com"
}
```

2. Login to get a token:

```
POST /api/auth/login
{
  "username": "your_username",
  "password": "your_password"
}
```

3. Use the returned token in the Authorization header:

```
Authorization: Bearer your_token_here
```

## API Documentation

### Public Endpoints

- `GET /` - Health check
- `GET /trade-env` - Get current trading environment (live/demo)
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register new user

### Protected Endpoints

- `GET /api/v1/accounts` - Get all trading accounts
- `GET /api/v1/account-summary/:account-id` - Get account summary
- `GET /api/v1/open-positions/:account-id` - Get open positions for account
- `GET /api/v1/backtest-ids` - Get all backtest IDs
- `GET /api/v1/backtest/:id` - Get backtest details
- `POST /api/v1/backtest` - Run a new backtest
- `POST /api/v1/trade` - Execute a live trade based on backtest

## Monitoring & Production Readiness

For production deployment, consider:

1. **Database**: Migrate to a dedicated PostgreSQL service:

   - AWS RDS for PostgreSQL
   - DigitalOcean Managed Databases
   - TimescaleDB Cloud (ideal for time-series data)

2. **Monitoring**:

   - Set up application monitoring (New Relic, Datadog)
   - Configure alerting for critical errors
   - Enable database query performance monitoring

3. **Backups**:
   - Schedule regular database backups
   - Set up point-in-time recovery
   - Test backup restoration periodically

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
