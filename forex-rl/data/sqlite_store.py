import sqlite3
from typing import List, Dict, Any
import threading

class CandleSQLiteStore:
    def __init__(self, db_path: str = 'data/forex_candles.sqlite3'):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS candles (
                    instrument TEXT NOT NULL,
                    time TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    PRIMARY KEY (instrument, time)
                )
            ''')
            conn.commit()

    def upsert_candles(self, instrument: str, candles: List[Dict[str, Any]]):
        """
        Upsert a list of candles for a given instrument.
        Each candle dict must have keys: time, open, high, low, close, volume
        """
        with self._lock, sqlite3.connect(self.db_path) as conn:
            data = [
                (
                    instrument,
                    c['time'].isoformat() if hasattr(c['time'], 'isoformat') else str(c['time']),
                    c['open'], c['high'], c['low'], c['close'], c['volume']
                )
                for c in candles
            ]
            conn.executemany('''
                INSERT OR REPLACE INTO candles (instrument, time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()

    def get_candles(self, instrument: str, start_time: str = None, end_time: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve candles for an instrument, optionally within a time range.
        """
        with sqlite3.connect(self.db_path) as conn:
            query = 'SELECT instrument, time, open, high, low, close, volume FROM candles WHERE instrument = ?'
            params = [instrument]
            if start_time:
                query += ' AND time >= ?'
                params.append(start_time)
            if end_time:
                query += ' AND time <= ?'
                params.append(end_time)
            query += ' ORDER BY time ASC'
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [
                {
                    'instrument': row[0],
                    'time': row[1],
                    'open': row[2],
                    'high': row[3],
                    'low': row[4],
                    'close': row[5],
                    'volume': row[6]
                } for row in rows
            ]
