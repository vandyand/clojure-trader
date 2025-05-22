import yfinance as yf
import pandas as pd

# Comprehensive macro ETF and proxy list (symbol: description)
etfs = {
    # Currency ETFs
    'UUP': 'Invesco DB US Dollar Index Bullish Fund',
    'FXE': 'Invesco CurrencyShares Euro Trust',
    'FXY': 'Invesco CurrencyShares Japanese Yen Trust',
    'FXB': 'Invesco CurrencyShares British Pound Sterling Trust',
    'FXF': 'Invesco CurrencyShares Swiss Franc Trust',
    'CEW': 'WisdomTree Emerging Currency Strategy Fund',
    'CYB': 'WisdomTree Chinese Yuan Strategy Fund',
    # Global Equity Indices
    'QQQ': 'Nasdaq 100',
    'DIA': 'Dow Jones Industrial Average',
    'EFA': 'iShares MSCI EAFE ETF',
    'EWJ': 'iShares MSCI Japan ETF',
    'EZU': 'iShares MSCI Eurozone ETF',
    'EEM': 'iShares MSCI Emerging Markets ETF',
    # Commodity & Volatility Proxies
    'DBC': 'Invesco DB Commodity Index Tracking Fund',
    'DBA': 'Invesco DB Agriculture Fund',
    'SLV': 'iShares Silver Trust',
    'VIXY': 'ProShares VIX Short-Term Futures ETF',
    'UNG': 'United States Natural Gas Fund',
    # Bonds & Rates
    'IEF': 'iShares 7-10 Year Treasury Bond ETF',
    'SHY': 'iShares 1-3 Year Treasury Bond ETF',
    'BWX': 'SPDR Bloomberg Barclays International Treasury Bond ETF',
    'EMB': 'iShares J.P. Morgan USD Emerging Markets Bond ETF',
    # Sectors & Thematic
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLI': 'Industrials',
    'VNQ': 'Real Estate',
    # Foreign/Other
    'BTC-USD': 'Bitcoin (USD)',
    'ASHR': 'Xtrackers Harvest CSI 300 China A-Shares ETF',
    'EWZ': 'iShares MSCI Brazil ETF',
}

for symbol, desc in etfs.items():
    try:
        print(f"Fetching {desc} ({symbol}) daily candles from Yahoo Finance...")
        df = yf.download(symbol, interval='1d', auto_adjust=False, progress=False)
        if df.empty:
            print(f"No data returned for {symbol}.")
            continue
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'timestamp'}, inplace=True)
        csv_filename = f"{symbol}_daily_yf.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Saved {len(df)} daily candles for {symbol} to {csv_filename}")
    except Exception as e:
        print(f"Error fetching {symbol}: {e}") 