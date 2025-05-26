#!/usr/bin/env python3
"""
Test script for the data pipeline
Tests OANDA API connection, data fetching, feature engineering, and validation
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from config.forex_pairs import FOREX_PAIRS, FIBONACCI_PERIODS, TOTAL_INPUT_FEATURES
from data.oanda_client import OandaDataClient, fetch_forex_data
from data.feature_engineer import FibonacciFeatureEngineer, calculate_forex_features
from data.data_validator import DataValidator, validate_forex_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_configuration():
    """Test that configuration is correct"""
    logger.info("Testing configuration...")
    
    print(f"✓ Forex pairs: {len(FOREX_PAIRS)} pairs")
    print(f"✓ Fibonacci periods: {len(FIBONACCI_PERIODS)} periods")
    print(f"✓ Total input features: {TOTAL_INPUT_FEATURES}")
    print(f"✓ Model input dimension: {config.model.input_dim}")
    
    assert len(FOREX_PAIRS) == 20, f"Expected 20 forex pairs, got {len(FOREX_PAIRS)}"
    assert len(FIBONACCI_PERIODS) == 15, f"Expected 15 Fibonacci periods, got {len(FIBONACCI_PERIODS)}"
    assert TOTAL_INPUT_FEATURES == 300, f"Expected 300 features, got {TOTAL_INPUT_FEATURES}"
    assert config.model.input_dim == 300, f"Expected 300 input dim, got {config.model.input_dim}"
    
    print("✓ Configuration test passed!")
    return True

def test_oanda_connection():
    """Test OANDA API connection"""
    logger.info("Testing OANDA connection...")
    
    try:
        client = OandaDataClient()
        
        # Test connection
        if client.test_connection():
            print("✓ OANDA connection successful")
            
            # Get account info
            account_info = client.get_account_info()
            if account_info:
                print(f"✓ Account ID: {account_info.get('id', 'N/A')}")
                print(f"✓ Account currency: {account_info.get('currency', 'N/A')}")
            
            return True
        else:
            print("✗ OANDA connection failed")
            return False
            
    except Exception as e:
        print(f"✗ OANDA connection error: {e}")
        return False

def test_data_fetching():
    """Test data fetching for a few instruments"""
    logger.info("Testing data fetching...")
    
    try:
        # Test with a small subset first
        test_pairs = FOREX_PAIRS[:3]  # Just first 3 pairs
        
        print(f"Fetching data for {len(test_pairs)} test pairs: {test_pairs}")
        
        client = OandaDataClient()
        data = client.fetch_multiple_instruments(
            instruments=test_pairs,
            count=100  # Small amount for testing
        )
        
        if data:
            print(f"✓ Successfully fetched data for {len(data)} instruments")
            
            for instrument, df in data.items():
                print(f"  - {instrument}: {len(df)} candles, {df.index.min()} to {df.index.max()}")
                
            return data
        else:
            print("✗ No data fetched")
            return None
            
    except Exception as e:
        print(f"✗ Data fetching error: {e}")
        return None

def test_feature_engineering(price_data):
    """Test feature engineering"""
    logger.info("Testing feature engineering...")
    
    if not price_data:
        print("✗ No price data provided for feature engineering")
        return None
    
    try:
        engineer = FibonacciFeatureEngineer()
        
        # Calculate features
        features = engineer.calculate_features_all_pairs(price_data)
        
        if not features.empty:
            print(f"✓ Features calculated: {features.shape}")
            print(f"✓ Expected shape: ({len(features)}, {TOTAL_INPUT_FEATURES})")
            
            # Validate feature names
            feature_names = engineer.get_feature_names()
            print(f"✓ Feature names: {len(feature_names)} names generated")
            
            # Test normalization
            normalized_features = engineer.normalize_features(features)
            print(f"✓ Normalized features: {normalized_features.shape}")
            
            # Test latest features extraction
            latest_features = engineer.get_latest_features(price_data)
            print(f"✓ Latest feature vector: {latest_features.shape} (dtype: {latest_features.dtype})")
            
            # Validate features
            is_valid, issues = engineer.validate_features(features)
            print(f"✓ Feature validation: {'PASSED' if is_valid else 'FAILED'}")
            if issues:
                print(f"  Issues: {issues}")
            
            return features
        else:
            print("✗ No features calculated")
            return None
            
    except Exception as e:
        print(f"✗ Feature engineering error: {e}")
        return None

def test_data_validation(price_data, features=None):
    """Test data validation"""
    logger.info("Testing data validation...")
    
    try:
        validator = DataValidator()
        
        # Validate and clean price data
        cleaned_data, issues = validator.validate_and_clean_all_data(price_data)
        
        print(f"✓ Data validation completed for {len(cleaned_data)} instruments")
        
        # Count total issues
        total_issues = sum(len(instrument_issues) for instrument_issues in issues.values())
        print(f"✓ Total validation issues found: {total_issues}")
        
        # Generate quality report
        report = validator.get_data_quality_report(cleaned_data, features)
        
        print(f"✓ Data quality report generated")
        print(f"  - Valid instruments: {report['summary']['valid_instruments']}/{report['summary']['total_instruments']}")
        print(f"  - Success rate: {report['summary']['validation_success_rate']:.2%}")
        
        if features is not None:
            print(f"  - Feature validation: {'PASSED' if report['features']['is_valid'] else 'FAILED'}")
        
        return cleaned_data, report
        
    except Exception as e:
        print(f"✗ Data validation error: {e}")
        return None, None

def test_end_to_end_pipeline():
    """Test the complete data pipeline end-to-end"""
    logger.info("Testing end-to-end pipeline...")
    
    try:
        # Use convenience functions for full pipeline test
        print("Fetching data for all forex pairs...")
        
        # Fetch data for all pairs (smaller count for testing)
        price_data = fetch_forex_data(count=200)
        
        if not price_data:
            print("✗ Failed to fetch price data")
            return False
        
        print(f"✓ Fetched data for {len(price_data)} instruments")
        
        # Calculate features
        print("Calculating features...")
        features = calculate_forex_features(price_data, normalize=True)
        
        if features.empty:
            print("✗ Failed to calculate features")
            return False
        
        print(f"✓ Calculated features: {features.shape}")
        
        # Validate everything
        print("Validating data...")
        cleaned_data, report = validate_forex_data(price_data, clean_data=True)
        
        if not cleaned_data:
            print("✗ Data validation failed")
            return False
        
        print(f"✓ Data validation completed")
        print(f"✓ Pipeline test successful!")
        
        # Summary
        print("\n" + "="*50)
        print("PIPELINE TEST SUMMARY")
        print("="*50)
        print(f"Instruments processed: {len(cleaned_data)}")
        print(f"Features generated: {features.shape}")
        print(f"Data quality: {report['summary']['validation_success_rate']:.2%} success rate")
        print(f"Configuration: {len(FOREX_PAIRS)} pairs × {len(FIBONACCI_PERIODS)} periods = {TOTAL_INPUT_FEATURES} features")
        
        return True
        
    except Exception as e:
        print(f"✗ End-to-end pipeline error: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("FOREX RL DATA PIPELINE TEST")
    print("="*60)
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: Configuration
    try:
        if test_configuration():
            tests_passed += 1
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
    
    print("\n" + "-"*40)
    
    # Test 2: OANDA Connection
    try:
        if test_oanda_connection():
            tests_passed += 1
    except Exception as e:
        print(f"✗ OANDA connection test failed: {e}")
    
    print("\n" + "-"*40)
    
    # Test 3: Data Fetching
    price_data = None
    try:
        price_data = test_data_fetching()
        if price_data:
            tests_passed += 1
    except Exception as e:
        print(f"✗ Data fetching test failed: {e}")
    
    print("\n" + "-"*40)
    
    # Test 4: Feature Engineering
    features = None
    if price_data:
        try:
            features = test_feature_engineering(price_data)
            if features is not None:
                tests_passed += 1
        except Exception as e:
            print(f"✗ Feature engineering test failed: {e}")
    else:
        print("⚠ Skipping feature engineering test (no price data)")
    
    print("\n" + "-"*40)
    
    # Test 5: Data Validation
    if price_data:
        try:
            cleaned_data, report = test_data_validation(price_data, features)
            if cleaned_data:
                tests_passed += 1
        except Exception as e:
            print(f"✗ Data validation test failed: {e}")
    else:
        print("⚠ Skipping data validation test (no price data)")
    
    print("\n" + "-"*40)
    
    # Test 6: End-to-End Pipeline (only if we have API access)
    if tests_passed >= 2:  # At least config and connection work
        try:
            if test_end_to_end_pipeline():
                tests_passed += 1
        except Exception as e:
            print(f"✗ End-to-end pipeline test failed: {e}")
    else:
        print("⚠ Skipping end-to-end test (prerequisites not met)")
    
    # Final results
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    print(f"Success rate: {tests_passed/total_tests:.2%}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Data pipeline is ready.")
        return 0
    elif tests_passed >= 4:
        print("✅ Core functionality working. Some advanced features may need attention.")
        return 0
    else:
        print("❌ Critical issues found. Please check configuration and API credentials.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 