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