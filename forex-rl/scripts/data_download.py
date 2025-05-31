#!/usr/bin/env python3
"""
Data download script for forex RL system
Downloads historical data from OANDA and stores it in SQLite database
"""

import sys
import os
import argparse
import logging
from datetime import datetime
import pandas as pd
import json
import sqlite3
import time
from tqdm import tqdm

import sys
import os

# Calculate the path to the project root (forex-rl directory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add the project root to the Python path
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

from forex_config.settings import config
from config.forex_pairs import FOREX_PAIRS
from data.oanda_client import OandaDataClient
from data.data_validator import DataValidator
from data.sqlite_store import CandleSQLiteStore
from config.oanda_config import oanda_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_historical_data(days: int = None, 
                           count: int = None,
                           instruments: list = None,
                           output_dir: str = None,
                           validate_data: bool = True,
                           store_in_db: bool = True) -> dict:
    """
    Download historical forex data and store in SQLite database
    
    Args:
        days: Number of days of historical data
        count: Number of candles (alternative to days)
        instruments: List of instruments (defaults to all)
        output_dir: Directory to save data
        validate_data: Whether to validate and clean data
        store_in_db: Whether to store in SQLite database
        
    Returns:
        Dictionary with download results
    """
    
    # Set defaults
    if instruments is None:
        instruments = FOREX_PAIRS
    
    if output_dir is None:
        output_dir = config.data_dir
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Starting data download for {len(instruments)} instruments")
    logger.info(f"Parameters: days={days}, count={count}, validate={validate_data}, store_in_db={store_in_db}")
    
    # Initialize OANDA client
    client = OandaDataClient(
        api_key=oanda_config.api_key,
        account_id=oanda_config.account_id,
        environment=oanda_config.environment
    )
    
    # Initialize SQLite store
    db_store = CandleSQLiteStore(db_path=os.path.join(output_dir, 'forex_candles.sqlite3'))
    
    # Download data
    logger.info("Fetching data from OANDA...")
    
    try:
        if days:
            price_data = client.fetch_multiple_instruments(
                instruments=instruments,
                granularity="D",  # Daily data
                count=days
            )
        else:
            price_data = client.fetch_multiple_instruments(
                instruments=instruments,
                granularity="D",  # Daily data
                count=count or 1000
            )
        
        if not price_data:
            logger.error("Failed to fetch any data")
            return {'success': False, 'error': 'No data fetched'}
        
        logger.info(f"Successfully fetched data for {len(price_data)} instruments")
        
        # Validate and clean data if requested
        cleaned_data = price_data
        validation_report = None
        
        if validate_data:
            logger.info("Validating and cleaning data...")
            validator = DataValidator()
            cleaned_data = {}
            validation_report = {'instruments': {}}
            
            for instrument, df in price_data.items():
                is_valid, issues = validator.validate_price_data(df, instrument)
                if not is_valid:
                    logger.warning(f"Data issues for {instrument}: {issues}")
                    # Clean the data
                    cleaned_df = validator.clean_price_data(df, instrument)
                    cleaned_data[instrument] = cleaned_df
                else:
                    cleaned_data[instrument] = df
                validation_report['instruments'][instrument] = {
                    'is_valid': is_valid,
                    'issues': issues
                }
            
            # Calculate overall success rate
            valid_count = sum(1 for inst in validation_report['instruments'].values() if inst['is_valid'])
            success_rate = valid_count / len(validation_report['instruments'])
            validation_report['summary'] = {
                'validation_success_rate': success_rate,
                'valid_instruments': valid_count,
                'total_instruments': len(validation_report['instruments'])
            }
            logger.info(f"Data validation complete: {success_rate:.2%} success rate")
        
        # Store in database if requested
        if store_in_db:
            logger.info("Storing data in SQLite database...")
            for instrument, df in tqdm(cleaned_data.items(), desc="Storing instruments"):
                # Prepare data for database
                candles = []
                for idx, row in df.iterrows():
                    candles.append({
                        'time': idx.isoformat(),
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    })
                try:
                    db_store.upsert_candles(instrument, candles)
                    logger.debug(f"Stored {len(candles)} candles for {instrument}")
                except Exception as e:
                    logger.error(f"Failed to store {instrument}: {str(e)}")
            logger.info("All instruments stored in database")
        
        # Create summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = {
            'timestamp': timestamp,
            'instruments_requested': len(instruments),
            'instruments_downloaded': len(cleaned_data),
            'data_points_per_instrument': {
                instrument: len(df) for instrument, df in cleaned_data.items()
            },
            'date_range': {
                'start': min(df.index.min() for df in cleaned_data.values() if not df.empty),
                'end': max(df.index.max() for df in cleaned_data.values() if not df.empty)
            } if cleaned_data else None,
            'validation_success_rate': validation_report['summary']['validation_success_rate'] if validation_report else None,
            'database_path': db_store.db_path if store_in_db else None
        }
        
        # Save summary
        summary_file = os.path.join(output_dir, f"download_summary_{timestamp}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Download summary saved to {summary_file}")
        
        return {
            'success': True,
            'summary': summary,
            'price_data': cleaned_data,
            'validation_report': validation_report
        }
        
    except Exception as e:
        logger.error(f"Download failed with exception: {str(e)}")
        return {'success': False, 'error': str(e)}

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Download forex data for RL training')
    
    # Data selection
    parser.add_argument('--days', type=int, help='Number of days of historical data')
    parser.add_argument('--count', type=int, default=1000, help='Number of candles (default: 1000)')
    parser.add_argument('--instruments', nargs='+', help='Specific instruments to download (default: all)')
    
    # Processing options
    parser.add_argument('--no-validate', action='store_true', help='Skip data validation')
    parser.add_argument('--no-db', action='store_true', help='Skip storing in database')
    
    # Output options
    parser.add_argument('--output-dir', default=None, help='Output directory (default: data/)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    # Presets
    parser.add_argument('--quick', action='store_true', help='Quick download (100 candles, 3 instruments)')
    parser.add_argument('--training', action='store_true', help='Training dataset (2000 candles, all instruments)')
    parser.add_argument('--full', action='store_true', help='Full dataset (5000 candles, all instruments)')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Apply presets
    if args.quick:
        args.count = 100
        args.instruments = FOREX_PAIRS[:3]
        logger.info("Quick preset: 100 candles, 3 instruments")
    elif args.training:
        args.count = 2000
        args.instruments = None  # All instruments
        logger.info("Training preset: 2000 candles, all instruments")
    elif args.full:
        args.count = 5000
        args.instruments = None  # All instruments
        logger.info("Full preset: 5000 candles, all instruments")
    
    # Download data
    result = download_historical_data(
        days=args.days,
        count=args.count,
        instruments=args.instruments,
        output_dir=args.output_dir,
        validate_data=not args.no_validate,
        store_in_db=not args.no_db
    )
    
    if not result['success']:
        logger.error(f"❌ Download failed: {result['error']}")
        sys.exit(1)
    
    logger.info("✅ Download complete!")
    logger.info(f"Summary: {result['summary']}")

if __name__ == '__main__':
    main()
