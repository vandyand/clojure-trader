CREATE TABLE IF NOT EXISTS candles_wide (
timestamp TIMESTAMPTZ NOT NULL,
instrument VARCHAR(20) NOT NULL,
granularity VARCHAR(10) NOT NULL,
    features JSONB NOT NULL,
PRIMARY KEY (timestamp, instrument, granularity)
);
