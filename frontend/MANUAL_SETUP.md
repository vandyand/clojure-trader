# Manual Supabase Setup Guide

This guide provides step-by-step instructions for setting up the required database table in Supabase for the Forex Trading Dashboard.

## Prerequisites

- A Supabase account
- Your Supabase project created at https://supabase.com

## Setup Steps

1. **Log in to your Supabase Dashboard** at https://supabase.com

2. **Navigate to the SQL Editor**:

   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Copy and paste the following SQL code**:

```sql
-- Create account_snapshots table
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

-- Create policy to allow anon users to insert data (for our dashboard app)
create policy "Allow anonymous users to insert data"
  on public.account_snapshots
  for insert
  to anon
  with check (true);

-- Create policy to allow anon users to select data (for our dashboard app)
create policy "Allow anonymous users to select data"
  on public.account_snapshots
  for select
  to anon
  using (true);
```

4. **Run the SQL script** by clicking the "Run" button

5. **Verify the table was created**:

   - Go to "Table Editor" in the left sidebar
   - You should see "account_snapshots" listed

6. **Update the .env File** in your project:
   - Ensure your `.env` file contains the correct Supabase URL and anon key:
   ```
   REACT_APP_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
   REACT_APP_SUPABASE_ANON_KEY=YOUR_ANON_KEY
   ```

Now your Supabase database is configured correctly for the Forex Trading Dashboard.

## Data Model Explanation

The `account_snapshots` table stores point-in-time snapshots of your trading account status:

- `id`: Unique identifier for each snapshot (automatically generated)
- `timestamp`: When the snapshot was taken
- `account_id`: Your Oanda account ID
- `balance`: Account balance
- `unrealized_pl`: Unrealized profit/loss
- `nav`: Net Asset Value
- `margin_used`: Amount of margin being used
- `margin_available`: Available margin
- `positions`: JSON array of all open positions
- `environment`: Whether this is from "LIVE" or "DEMO" account

The dashboard will automatically insert a new snapshot each time it refreshes the account data, building up a history of your account performance over time.
