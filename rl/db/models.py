from sqlalchemy import Column, String, Float, DateTime, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Candle(Base):
    __tablename__ = 'candles'
    timestamp = Column(DateTime, nullable=False)
    instrument = Column(String(20), nullable=False)
    granularity = Column(String(10), nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    bid_open = Column(Float)
    bid_high = Column(Float)
    bid_low = Column(Float)
    bid_close = Column(Float)
    ask_open = Column(Float)
    ask_high = Column(Float)
    ask_low = Column(Float)
    ask_close = Column(Float)
    spread = Column(Float)
    tick_volume = Column(Float)
    sma_20 = Column(Float)
    ema_20 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
    bb_bbm = Column(Float)
    bb_bbh = Column(Float)
    bb_bbl = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    cci = Column(Float)
    adx = Column(Float)
    williams_r = Column(Float)
    obv = Column(Float)
    atr = Column(Float)
    roc = Column(Float)
    mfi = Column(Float)
    # Dynamically add feature_1 to feature_400
    __table_args__ = (
        PrimaryKeyConstraint('timestamp', 'instrument', 'granularity', name='candles_pk'),
    )

# Dynamically add feature_1 to feature_400 as class attributes
for i in range(1, 401):
    setattr(Candle, f'feature_{i}', Column(Float)) 