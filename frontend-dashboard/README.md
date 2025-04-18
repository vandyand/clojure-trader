# Forex Trading Dashboard

A read-only dashboard for monitoring Oanda trading account performance built with React and TypeScript. The dashboard features:

- Real-time account summary data
- Position monitoring
- Performance tracking with historical data visualization
- Data persistence using Supabase

## Setup Instructions

### Prerequisites

- Node.js (v14+)
- Oanda API keys (Demo and/or Live)
- Supabase account

### Supabase Setup

#### Option 1: Automated Setup (Recommended)

1. Create a new Supabase project at https://supabase.com
2. Get your Supabase URL and API key from the project settings
3. Add them to your `.env` file
4. Run the setup script:

```bash
npm run setup-supabase
```

This will automatically create the necessary tables and permissions.

#### Option 2: Manual Setup

1. Create a new Supabase project at https://supabase.com
2. Create a new table called `account_snapshots` with the following schema:

```sql
create table public.account_snapshots (
  id uuid not null default uuid_generate_v4(),
  timestamp timestamptz not null,
  account_id text not null,
  balance numeric not null,
  unrealized_pl numeric not null,
  nav numeric not null,
  margin_used numeric not null,
  margin_available numeric not null,
  positions jsonb not null,
  environment text not null,

  constraint account_snapshots_pkey primary key (id)
);

-- Create index for faster queries
create index account_snapshots_timestamp_idx on public.account_snapshots (timestamp);

-- Set up row level security
alter table public.account_snapshots enable row level security;

-- Create policy to allow all operations for authenticated users
create policy "Allow all operations for authenticated users"
  on public.account_snapshots
  for all
  to authenticated
  using (true);
```

3. Get your Supabase URL and API key from the project settings

### Environment Setup

1. Copy your Supabase URL to the `.env` file
2. Ensure you have the following environment variables set:
   - `SUPABASE_API_KEY`
   - `OANDA_LIVE_KEY`
   - `OANDA_DEMO_KEY`

### Installation

1. Install dependencies:

```bash
npm install
```

2. Start the development server:

```bash
npm start
```

3. Build for production:

```bash
npm run build
```

## API Key Security Update

We've improved security by moving all Oanda API keys to the server side only. The application now uses a simple Express server that proxies requests to Oanda, keeping API keys secure.

### Local Development

1. Create `.env.server` file with your Oanda API keys (this file should never be committed):

```
# Oanda API Settings
REACT_APP_OANDA_LIVE_OR_DEMO=LIVE
REACT_APP_OANDA_LIVE_URL=https://api-fxtrade.oanda.com/v3/
REACT_APP_OANDA_DEMO_URL=https://api-fxpractice.oanda.com/v3/
REACT_APP_OANDA_LIVE_ACCOUNT_ID=your-live-account-id
REACT_APP_OANDA_DEMO_ACCOUNT_ID=your-demo-account-id
REACT_APP_OANDA_LIVE_KEY=your-live-api-key
REACT_APP_OANDA_DEMO_KEY=your-demo-api-key
```

2. For development with hot reloading (React frontend only):

```
npm run dev
```

3. To run both server and frontend (after build):

```
npm run build
npm start
```

### Heroku Deployment

1. Add your environment variables to Heroku:

```
heroku config:set REACT_APP_OANDA_LIVE_OR_DEMO=LIVE
heroku config:set REACT_APP_OANDA_LIVE_URL=https://api-fxtrade.oanda.com/v3/
heroku config:set REACT_APP_OANDA_DEMO_URL=https://api-fxpractice.oanda.com/v3/
heroku config:set REACT_APP_OANDA_LIVE_ACCOUNT_ID=your-live-account-id
heroku config:set REACT_APP_OANDA_DEMO_ACCOUNT_ID=your-demo-account-id
heroku config:set REACT_APP_OANDA_LIVE_KEY=your-live-api-key
heroku config:set REACT_APP_OANDA_DEMO_KEY=your-demo-api-key
```

2. Deploy to Heroku:

```
git push heroku main
```

## Notes

- Data is stored in Supabase each time the account summary is fetched
- Historical performance data is built up over time as you use the dashboard
- Switch between DEMO and LIVE environments by changing the `REACT_APP_OANDA_LIVE_OR_DEMO` environment variable

## License

MIT
