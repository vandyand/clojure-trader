#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our feature adapter and ETF fetcher
from rl.data.quick_etf_fetch import fetch_multiple_etfs, calculate_basic_features
from rl.data.feature_adapter import create_fixed_size_feature_vector

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("integrated_trader")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Integrated RL Trader with ETF Support")
    
    parser.add_argument("--account-size", type=float, default=1000.0,
                        help="Account size in USD")
    parser.add_argument("--risk-percent", type=float, default=5.0,
                        help="Risk percentage (1-100)")
    parser.add_argument("--model-path", type=str, default="models/rl_trader.pt",
                        help="Path to trained model")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Run in dry-run mode (no actual trades)")
    parser.add_argument("--etf-period", type=str, default="1mo",
                        help="Period for ETF data (e.g., 1d, 1mo, 1y)")
                        
    return parser.parse_args()

def fetch_etf_data(period="1mo"):
    """Fetch ETF data using our simplified approach"""
    logger.info(f"Fetching ETF data with period {period}")
    
    # List of ETFs to fetch
    etfs = ["SPY", "QQQ", "IWM", "GLD", "SLV", "VXX", "EEM", "XLF", "XLE"]
    
    # Fetch data
    etf_data = fetch_multiple_etfs(etfs, period=period)
    
    # Calculate features and prepare result
    results = {}
    for symbol, df in etf_data.items():
        if df is not None and not df.empty:
            features = calculate_basic_features(df)
            
            # Add to results
            results[symbol] = {
                "last_price": float(df['close'].iloc[-1]),
                "daily_change_pct": float(df['close'].pct_change().iloc[-1] * 100),
                "ma_20": float(features['sma_20'].iloc[-1]) if 'sma_20' in features else 0,
                "ma_50": float(features['sma_50'].iloc[-1]) if 'sma_50' in features else 0,
                "volatility": float(features['std_20'].iloc[-1]) if 'std_20' in features else 0,
                "timestamp": datetime.now().isoformat()
            }
    
    # Save ETF data to file for the main system to use
    os.makedirs("etf_data", exist_ok=True)
    with open("etf_data/etf_summary.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Saved ETF data for {len(results)} symbols")
    return results

def inject_etf_features():
    """
    Inject ETF features into the system by modifying the data_fetcher.py prepare_feature_vector 
    function at runtime
    """
    try:
        from rl.data.feature_adapter import get_adapted_feature_vector
        from rl.data_fetcher import DataFetcher
        
        # Monkey patch the DataFetcher prepare_feature_vector method
        original_prepare_feature_vector = DataFetcher.prepare_feature_vector
        
        def patched_prepare_feature_vector(self):
            """Patched method that handles feature vector sizing properly"""
            try:
                # First try the original method
                feature_vector = original_prepare_feature_vector(self)
                
                if feature_vector is not None:
                    # Check feature vector size and adjust if needed
                    expected_size = 1084  # Expected model input size
                    current_size = len(feature_vector)
                    
                    if current_size != expected_size:
                        logger.warning(f"Feature vector length mismatch: got {current_size}, expected {expected_size}")
                        
                        if current_size < expected_size:
                            # Pad with zeros
                            import numpy as np
                            padding = np.zeros(expected_size - current_size, dtype=np.float32)
                            feature_vector = np.concatenate([feature_vector, padding])
                            logger.info(f"Padded feature vector from {current_size} to {expected_size}")
                        elif current_size > expected_size:
                            # Truncate
                            feature_vector = feature_vector[:expected_size]
                            logger.info(f"Truncated feature vector from {current_size} to {expected_size}")
                    
                    logger.info(f"Final feature vector shape: {feature_vector.shape}")
                return feature_vector
            except Exception as e:
                logger.error(f"Error in patched prepare_feature_vector: {e}")
                return None
        
        # Apply the patch
        DataFetcher.prepare_feature_vector = patched_prepare_feature_vector
        logger.info("Successfully patched DataFetcher.prepare_feature_vector")
        
    except Exception as e:
        logger.error(f"Failed to patch DataFetcher.prepare_feature_vector: {e}")

def run_generate_signals(args):
    """Run the signal generator with appropriate arguments"""
    logger.info("Running signal generator")
    
    cmd = [
        sys.executable,
        os.path.join(parent_dir, "rl", "generate_signals.py"),
        "--account-size", str(args.account_size),
        "--risk-percent", str(args.risk_percent),
        "--model-path", args.model_path
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    # Print output
    if stdout:
        logger.info(f"Signal generator output:\n{stdout.decode()}")
    if stderr:
        logger.info(f"Signal generator stderr:\n{stderr.decode()}")
    
    return process.returncode

def run_integrated_system():
    """Run the integrated trading system"""
    args = parse_args()
    
    logger.info(f"Starting integrated trading system")
    logger.info(f"Account size: ${args.account_size}")
    logger.info(f"Risk percent: {args.risk_percent}%")
    logger.info(f"Model path: {args.model_path}")
    logger.info(f"Dry run: {args.dry_run}")
    
    # Step 1: Fetch ETF data using our simplified approach
    etf_data = fetch_etf_data(period=args.etf_period)
    
    # Step 2: Patch the data fetcher to handle feature vector size
    inject_etf_features()
    
    # Step 3: Run the signal generator
    exit_code = run_generate_signals(args)
    
    # Step 4: Process results
    try:
        # Check for signal files
        signal_files = [f for f in os.listdir("signals") if f.endswith(".json")]
        if signal_files:
            latest_signal_file = sorted(signal_files)[-1]
            logger.info(f"Found signal file: {latest_signal_file}")
            
            with open(os.path.join("signals", latest_signal_file), 'r') as f:
                signals = json.load(f)
            
            logger.info("\n===== TRADING SIGNALS =====")
            logger.info(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("Instrument   |   Direction   |   Position Size   |   USD Amount")
            logger.info("------------------------------------------------------------------")
            
            for position in signals.get("positions", []):
                instrument = position.get("instrument", "")
                direction = position.get("direction", "NEUTRAL")
                position_size = position.get("position_size", 0)
                usd_amount = position.get("usd_amount", 0)
                
                logger.info(f"{instrument:<12} | {direction:<12} | {position_size:<15.2f} | ${usd_amount:<10.2f}")
        else:
            logger.warning("No signal files found")
    except Exception as e:
        logger.error(f"Error processing signals: {e}")
    
    logger.info("Integrated trading completed")
    return 0

if __name__ == "__main__":
    sys.exit(run_integrated_system()) 