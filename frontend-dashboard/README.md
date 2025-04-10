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

## Deployment to Heroku

### Prerequisites

- Heroku CLI installed
- Heroku account

### Steps

1. Create a new Heroku app:

```bash
heroku create your-app-name
```

2. Set the buildpack:

```bash
heroku buildpacks:set heroku/nodejs
```

3. Set environment variables:

```bash
heroku config:set REACT_APP_SUPABASE_URL=your_supabase_url
heroku config:set REACT_APP_SUPABASE_API_KEY=your_supabase_api_key
heroku config:set REACT_APP_OANDA_LIVE_OR_DEMO=LIVE_OR_DEMO
heroku config:set REACT_APP_OANDA_LIVE_KEY=your_oanda_live_key
heroku config:set REACT_APP_OANDA_DEMO_KEY=your_oanda_demo_key
```

4. Deploy the app:

```bash
git add .
git commit -m "Initial deploy"
git push heroku main
```

## Notes

- Data is stored in Supabase each time the account summary is fetched
- Historical performance data is built up over time as you use the dashboard
- Switch between DEMO and LIVE environments by changing the `REACT_APP_OANDA_LIVE_OR_DEMO` environment variable

## License

MIT
