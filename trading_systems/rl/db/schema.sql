CREATE TABLE IF NOT EXISTS candles (
    timestamp TIMESTAMPTZ NOT NULL,
    instrument VARCHAR(20) NOT NULL,
    granularity VARCHAR(10) NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    bid_open DOUBLE PRECISION,
    bid_high DOUBLE PRECISION,
    bid_low DOUBLE PRECISION,
    bid_close DOUBLE PRECISION,
    ask_open DOUBLE PRECISION,
    ask_high DOUBLE PRECISION,
    ask_low DOUBLE PRECISION,
    ask_close DOUBLE PRECISION,
    spread DOUBLE PRECISION,
    tick_volume DOUBLE PRECISION,
    -- 400 feature columns
    feature_1 DOUBLE PRECISION,
    feature_2 DOUBLE PRECISION,
    feature_3 DOUBLE PRECISION,
    feature_4 DOUBLE PRECISION,
    feature_5 DOUBLE PRECISION,
    feature_6 DOUBLE PRECISION,
    feature_7 DOUBLE PRECISION,
    feature_8 DOUBLE PRECISION,
    feature_9 DOUBLE PRECISION,
    feature_10 DOUBLE PRECISION,
    -- ...
    feature_400 DOUBLE PRECISION,
    PRIMARY KEY (timestamp, instrument, granularity)
);

-- Convert to hypertable for TimescaleDB, partition by instrument
SELECT create_hypertable('candles', 'timestamp', partitioning_column => 'instrument', number_partitions => 20, if_not_exists => TRUE);

-- Create composite index for fast queries
CREATE INDEX IF NOT EXISTS idx_instrument_time ON candles (instrument, timestamp);

-- Enable compression
ALTER TABLE candles SET (timescaledb.compress, timescaledb.compress_orderby = 'instrument, timestamp'); 