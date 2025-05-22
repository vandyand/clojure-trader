import os
import pandas as pd
from rl.data.ingest import ingest_etf_candles

ETF_DIR = 'python-robinhood-wrapper'  # Updated to correct ETF CSV directory
REQUIRED_COLS = ['open', 'high', 'low', 'close', 'volume']

def main():
    csv_files = [f for f in os.listdir(ETF_DIR) if f.endswith('.csv') and '_daily_' in f]
    for csv_file in csv_files:
        instrument = os.path.basename(csv_file).split('_daily_')[0]
        path = os.path.join(ETF_DIR, csv_file)
        print(f"Processing {instrument} from {path}")
        df = pd.read_csv(path)
        # Remove non-numeric second row if present
        if pd.isna(pd.to_datetime(df.iloc[0,0], errors='coerce')):
            df = df.iloc[1:].reset_index(drop=True)
        # Standardize column names
        col_map = {c.lower().replace(' ', '').replace('adjclose', 'adj_close'): c for c in df.columns}
        missing = [col for col in REQUIRED_COLS if col_map.get(col, col.capitalize()) not in df.columns]
        if missing:
            print(f"Skipping {csv_file}: missing columns {missing}")
            continue
        df_std = pd.DataFrame()
        df_std['timestamp'] = pd.to_datetime(df[col_map.get('timestamp', 'timestamp')])
        for col in REQUIRED_COLS:
            df_std[col] = pd.to_numeric(df[col_map.get(col, col.capitalize())], errors='coerce')
        ingest_etf_candles(df_std, instrument, 'D')

if __name__ == '__main__':
    main() 