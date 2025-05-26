#!/usr/bin/env python3
"""
Data download script for forex RL system
Downloads historical data from OANDA and saves it for training
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd
import pickle

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from config.forex_pairs import FOREX_PAIRS
from data.oanda_client import OandaDataClient, fetch_forex_data
from data.feature_engineer import FibonacciFeatureEngineer, calculate_forex_features
from data.data_validator import DataValidator, validate_forex_data

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
                           calculate_features: bool = True) -> dict:
    """
    Download historical forex data
    
    Args:
        days: Number of days of historical data
        count: Number of candles (alternative to days)
        instruments: List of instruments (defaults to all)
        output_dir: Directory to save data
        validate_data: Whether to validate and clean data
        calculate_features: Whether to calculate features
        
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
    logger.info(f"Parameters: days={days}, count={count}, validate={validate_data}, features={calculate_features}")
    
    # Download data
    logger.info("Fetching data from OANDA...")
    
    if days:
        price_data = fetch_forex_data(instruments=instruments, days=days)
    else:
        price_data = fetch_forex_data(instruments=instruments, count=count or 1000)
    
    if not price_data:
        logger.error("Failed to fetch any data")
        return {'success': False, 'error': 'No data fetched'}
    
    logger.info(f"Successfully fetched data for {len(price_data)} instruments")
    
    # Validate and clean data if requested
    cleaned_data = price_data
    validation_report = None
    
    if validate_data:
        logger.info("Validating and cleaning data...")
        cleaned_data, validation_report = validate_forex_data(price_data, clean_data=True)
        
        if validation_report:
            success_rate = validation_report['summary']['validation_success_rate']
            logger.info(f"Data validation complete: {success_rate:.2%} success rate")
    
    # Calculate features if requested
    features = None
    if calculate_features:
        logger.info("Calculating features...")
        features = calculate_forex_features(cleaned_data, normalize=True)
        
        if not features.empty:
            logger.info(f"Features calculated: {features.shape}")
        else:
            logger.warning("Failed to calculate features")
    
    # Save data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw price data
    price_data_file = os.path.join(output_dir, f"price_data_{timestamp}.pkl")
    with open(price_data_file, 'wb') as f:
        pickle.dump(cleaned_data, f)
    logger.info(f"Price data saved to {price_data_file}")
    
    # Save features if calculated
    features_file = None
    if features is not None and not features.empty:
        features_file = os.path.join(output_dir, f"features_{timestamp}.pkl")
        features.to_pickle(features_file)
        logger.info(f"Features saved to {features_file}")
    
    # Save validation report if available
    report_file = None
    if validation_report:
        report_file = os.path.join(output_dir, f"validation_report_{timestamp}.json")
        validator = DataValidator()
        validator.save_validation_report(validation_report, report_file)
    
    # Create summary
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
        'features_shape': features.shape if features is not None else None,
        'validation_success_rate': validation_report['summary']['validation_success_rate'] if validation_report else None,
        'files': {
            'price_data': price_data_file,
            'features': features_file,
            'validation_report': report_file
        }
    }
    
    # Save summary
    summary_file = os.path.join(output_dir, f"download_summary_{timestamp}.json")
    import json
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"Download summary saved to {summary_file}")
    
    return {
        'success': True,
        'summary': summary,
        'price_data': cleaned_data,
        'features': features,
        'validation_report': validation_report
    }

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Download forex data for RL training')
    
    # Data selection
    parser.add_argument('--days', type=int, help='Number of days of historical data')
    parser.add_argument('--count', type=int, default=1000, help='Number of candles (default: 1000)')
    parser.add_argument('--instruments', nargs='+', help='Specific instruments to download (default: all)')
    
    # Processing options
    parser.add_argument('--no-validate', action='store_true', help='Skip data validation')
    parser.add_argument('--no-features', action='store_true', help='Skip feature calculation')
    
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
    
    # Validate arguments
    if args.days and args.count:
        logger.warning("Both --days and --count specified, using --days")
        args.count = None
    
    if not args.days and not args.count:
        args.count = 1000
        logger.info("No time period specified, using default 1000 candles")
    
    # Download data
    try:
        result = download_historical_data(
            days=args.days,
            count=args.count,
            instruments=args.instruments,
            output_dir=args.output_dir,
            validate_data=not args.no_validate,
            calculate_features=not args.no_features
        )
        
        if result['success']:
            summary = result['summary']
            print("\n" + "="*60)
            print("DOWNLOAD COMPLETE")
            print("="*60)
            print(f"Timestamp: {summary['timestamp']}")
            print(f"Instruments: {summary['instruments_downloaded']}/{summary['instruments_requested']}")
            
            if summary['date_range']:
                print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
            
            if summary['features_shape']:
                print(f"Features: {summary['features_shape']}")
            
            if summary['validation_success_rate'] is not None:
                print(f"Validation success: {summary['validation_success_rate']:.2%}")
            
            print(f"\nFiles saved:")
            for file_type, filepath in summary['files'].items():
                if filepath:
                    print(f"  {file_type}: {filepath}")
            
            print("\n✅ Data download successful!")
            return 0
        else:
            print(f"\n❌ Download failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        logger.error(f"Download failed with exception: {e}")
        print(f"\n❌ Download failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 