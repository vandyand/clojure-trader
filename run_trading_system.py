#!/usr/bin/env python3
import os
import sys
import time
import datetime
import subprocess
import traceback
import json
import argparse
from pathlib import Path

def ensure_directory_exists(path):
    """Ensure that a directory exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)

def log_message(message, log_file):
    """Log a message to both console and log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    
    print(formatted_message)
    
    with open(log_file, 'a') as f:
        f.write(formatted_message + "\n")

def run_command(command, log_file):
    """Run a shell command and log the output."""
    log_message(f"Running command: {command}", log_file)
    
    try:
        # Run the command and capture output
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        
        # Log output
        if stdout:
            log_message(f"Command output:\n{stdout}", log_file)
        if stderr:
            log_message(f"Command errors:\n{stderr}", log_file)
            
        if process.returncode != 0:
            log_message(f"Command failed with exit code {process.returncode}", log_file)
            return False
        else:
            log_message("Command completed successfully", log_file)
            return True
            
    except Exception as e:
        log_message(f"Error running command: {e}\n{traceback.format_exc()}", log_file)
        return False

def get_latest_position_sizes(signals_dir, log_file):
    """
    Get the most recent position sizes file
    
    Args:
        signals_dir: Directory with signal files
        log_file: Log file to write messages to
        
    Returns:
        Dictionary with position data or None if not found
    """
    try:
        # List all position size files
        position_files = [f for f in os.listdir(signals_dir) if f.startswith("position_sizes_") and f.endswith(".json")]
        
        if not position_files:
            log_message("No position size files found", log_file)
            return None
        
        # Sort by filename (which includes timestamp)
        position_files.sort(reverse=True)
        latest_file = os.path.join(signals_dir, position_files[0])
        
        log_message(f"Loading latest position sizes from {latest_file}", log_file)
        
        with open(latest_file, 'r') as f:
            position_data = json.load(f)
            
        log_message(f"Loaded position data with {len(position_data['positions'])} positions", log_file)
        return position_data
        
    except Exception as e:
        log_message(f"Error getting latest position sizes: {e}", log_file)
        return None

def get_latest_market_regimes(signals_dir, log_file):
    """
    Get the most recent market regime analysis file
    
    Args:
        signals_dir: Directory with signal files
        log_file: Log file to write messages to
        
    Returns:
        Dictionary with regime data or None if not found
    """
    try:
        # List all regime files
        regimes_dir = os.path.join(signals_dir, "regimes")
        if not os.path.exists(regimes_dir):
            log_message("Regimes directory does not exist", log_file)
            return None
            
        regime_files = [f for f in os.listdir(regimes_dir) if f.startswith("regimes_") and f.endswith(".json")]
        
        if not regime_files:
            log_message("No regime files found", log_file)
            return None
        
        # Sort by filename (which includes timestamp)
        regime_files.sort(reverse=True)
        latest_file = os.path.join(regimes_dir, regime_files[0])
        
        log_message(f"Loading latest market regimes from {latest_file}", log_file)
        
        with open(latest_file, 'r') as f:
            regime_data = json.load(f)
            
        log_message(f"Loaded regime data with {len(regime_data.get('regimes', {}))} regimes", log_file)
        return regime_data
        
    except Exception as e:
        log_message(f"Error getting latest market regimes: {e}", log_file)
        return None

def analyze_market_conditions(position_data, regime_data, log_file):
    """
    Analyze market conditions based on regime data
    
    Args:
        position_data: Position size data
        regime_data: Market regime data
        log_file: Log file to write messages to
        
    Returns:
        Dictionary with market analysis
    """
    if not regime_data or 'regimes' not in regime_data:
        log_message("No regime data available for market analysis", log_file)
        return None
        
    try:
        log_message("Analyzing market conditions:", log_file)
        
        regimes = regime_data['regimes']
        
        # Count regimes by type
        regime_counts = {}
        for instrument, data in regimes.items():
            regime_name = data.get('regime_name', 'UNKNOWN')
            regime_counts[regime_name] = regime_counts.get(regime_name, 0) + 1
            
        # Log regime distribution
        log_message("Market regime distribution:", log_file)
        for regime, count in regime_counts.items():
            log_message(f"  {regime}: {count} instruments", log_file)
            
        # Check if any instruments are in volatile regime
        volatile_instruments = [instr for instr, data in regimes.items() 
                               if data.get('regime_name') == 'VOLATILE']
        
        if volatile_instruments:
            log_message(f"Warning: {len(volatile_instruments)} instruments in VOLATILE regime", log_file)
            log_message(f"  Volatile instruments: {', '.join(volatile_instruments)}", log_file)
        
        # Overall market assessment
        bull_count = regime_counts.get('BULL', 0) + regime_counts.get('STRONG_BULL', 0)
        bear_count = regime_counts.get('BEAR', 0) + regime_counts.get('STRONG_BEAR', 0)
        neutral_count = regime_counts.get('NEUTRAL', 0)
        volatile_count = regime_counts.get('VOLATILE', 0)
        
        total_instruments = sum(regime_counts.values())
        
        # Calculate sentiment score (-1 to 1)
        sentiment_score = (bull_count - bear_count) / total_instruments if total_instruments > 0 else 0
        
        market_status = {
            'sentiment_score': sentiment_score,
            'bull_percent': (bull_count / total_instruments) * 100 if total_instruments > 0 else 0,
            'bear_percent': (bear_count / total_instruments) * 100 if total_instruments > 0 else 0,
            'neutral_percent': (neutral_count / total_instruments) * 100 if total_instruments > 0 else 0,
            'volatile_percent': (volatile_count / total_instruments) * 100 if total_instruments > 0 else 0,
            'regime_counts': regime_counts,
            'volatile_instruments': volatile_instruments
        }
        
        # Overall market assessment
        if sentiment_score > 0.5:
            market_status['overall_market'] = "STRONGLY BULLISH"
        elif sentiment_score > 0.2:
            market_status['overall_market'] = "BULLISH"
        elif sentiment_score < -0.5:
            market_status['overall_market'] = "STRONGLY BEARISH"
        elif sentiment_score < -0.2:
            market_status['overall_market'] = "BEARISH"
        else:
            market_status['overall_market'] = "NEUTRAL"
            
        # Volatility assessment
        if volatile_count / total_instruments > 0.2:
            market_status['volatility'] = "HIGH"
        elif volatile_count / total_instruments > 0.1:
            market_status['volatility'] = "MODERATE"
        else:
            market_status['volatility'] = "LOW"
            
        log_message(f"Overall market assessment: {market_status['overall_market']} with {market_status['volatility']} volatility", log_file)
        
        return market_status
        
    except Exception as e:
        log_message(f"Error analyzing market conditions: {e}", log_file)
        return None

def submit_to_broker(position_data, market_analysis, log_file, dry_run=True):
    """
    Submit position data to broker API
    
    Args:
        position_data: Position size data
        market_analysis: Market analysis data (can be None)
        log_file: Log file to write messages to
        dry_run: If True, don't actually submit orders
        
    Returns:
        True if successful, False otherwise
    """
    try:
        log_message("Submitting positions to broker:", log_file)
        
        positions = position_data["positions"]
        log_message(f"Account size: ${position_data['account_size']:.2f}", log_file)
        
        # Handle adaptive risk adjustment
        if 'risk_percent' in position_data:
            log_message(f"Risk percentage: {position_data['risk_percent']:.2f}%", log_file)
        else:
            log_message(f"Risk amount: ${position_data['risk_amount']:.2f}", log_file)
        
        # Print market analysis if available
        if market_analysis:
            log_message(f"Market conditions: {market_analysis['overall_market']} (Volatility: {market_analysis['volatility']})", log_file)
        
        # Separate forex and ETF positions
        forex_positions = []
        etf_positions = []
        
        # Import constants for OANDA instruments
        from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
        
        for pos in positions:
            instrument = pos['instrument']
            
            # Determine if this is a forex or ETF position
            if instrument in PAIRS_BY_LIQUIDITY_OANDA:
                forex_positions.append(pos)
            else:
                etf_positions.append(pos)
            
            # Log position details
            position_info = f"  {instrument}: {pos['direction']} {pos['position_size']:.6f} units (${pos['usd_amount']:.2f})"
            
            # Add regime info if available
            if 'regime' in pos:
                position_info += f" [{pos['regime']}]"
                
            # Add instrument type for clarity
            position_info += f" {'[FOREX]' if instrument in PAIRS_BY_LIQUIDITY_OANDA else '[ETF]'}"
                
            log_message(position_info, log_file)
        
        if dry_run:
            log_message("DRY RUN: Orders not actually submitted to broker", log_file)
            return True
        else:
            # Submit forex positions to OANDA
            if forex_positions:
                log_message(f"Submitting {len(forex_positions)} forex positions to OANDA", log_file)
                
                # Import OANDA API functions
                from api.oanda_api import create_order, close_position
                
                # Process each position
                for pos in forex_positions:
                    instrument = pos['instrument']
                    direction = pos['direction']
                    position_size = pos['position_size']
                    
                    # Determine units (positive for long, negative for short)
                    units = position_size if direction == "LONG" else -position_size
                    
                    if units != 0:
                        # Create the order
                        response = create_order(instrument, units)
                        log_message(f"OANDA order for {instrument}: {response}", log_file)
                    else:
                        # Close position if units is 0
                        response = close_position(instrument)
                        log_message(f"OANDA close position for {instrument}: {response}", log_file)
            
            # Submit ETF positions (would need implementation with a stock/ETF broker API)
            if etf_positions:
                log_message(f"ETF positions: {len(etf_positions)} positions would be submitted to stock/ETF broker", log_file)
                log_message("Note: Stock/ETF broker integration not yet implemented - these are simulated only", log_file)
                
                # Here you would add code to submit orders to a stock/ETF broker API
                # For example: Alpaca, Interactive Brokers, etc.
                
            return True
            
    except Exception as e:
        log_message(f"Error submitting to broker: {e}", log_file)
        return False

def refresh_etf_data(log_file):
    """
    Refresh ETF data before running a trading cycle
    
    Args:
        log_file: Log file to write messages to
        
    Returns:
        True if successful, False otherwise
    """
    log_message("Refreshing ETF data from yfinance", log_file)
    
    # Run the ETF data ingestion script
    etf_data_cmd = f"{sys.executable} {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rl/data/etf_data_ingestion.py')} --period 1y --generate-features"
    
    return run_command(etf_data_cmd, log_file)

def run_trading_cycle(account_size, risk_percent, model_path, use_regime_detection=True, 
                      adapt_position_sizing=True, refresh_etf=True, dry_run=True):
    """
    Run a full trading cycle including signal generation and order submission
    
    Args:
        account_size: Account size in USD
        risk_percent: Maximum percentage of account to risk daily
        model_path: Path to the trained RL model
        use_regime_detection: Whether to use market regime detection
        adapt_position_sizing: Whether to adapt position sizing based on regimes
        refresh_etf: Whether to refresh ETF data before running
        dry_run: If True, don't actually submit orders
        
    Returns:
        True if successful, False otherwise
    """
    # Setup
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    signals_dir = os.path.join(base_dir, "signals")
    
    # Ensure directories exist
    ensure_directory_exists(logs_dir)
    ensure_directory_exists(signals_dir)
    ensure_directory_exists(os.path.join(signals_dir, "regimes"))
    
    # Create log file for this run
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"trading_system_{timestamp}.log")
    
    log_message(f"Starting trading cycle with account size ${account_size} and risk {risk_percent}%", log_file)
    log_message(f"Market regime detection: {'Enabled' if use_regime_detection else 'Disabled'}", log_file)
    log_message(f"Adaptive position sizing: {'Enabled' if adapt_position_sizing else 'Disabled'}", log_file)
    log_message(f"ETF data refresh: {'Enabled' if refresh_etf else 'Disabled'}", log_file)
    
    # Refresh ETF data if enabled
    if refresh_etf:
        if not refresh_etf_data(log_file):
            log_message("Warning: Failed to refresh ETF data. Continuing with existing data.", log_file)
    
    # Generate trading signals with position sizing
    signals_cmd = (
        f"{sys.executable} {os.path.join(base_dir, 'rl/generate_signals.py')} "
        f"--account-size {account_size} --risk-percent {risk_percent} --model-path {model_path}"
    )
    
    # Add regime detection flags if enabled
    if use_regime_detection:
        signals_cmd += " --use-regime-detection"
    if adapt_position_sizing:
        signals_cmd += " --adapt-position-sizing"
    
    if not run_command(signals_cmd, log_file):
        log_message("Failed to generate trading signals - aborting cycle", log_file)
        return False
    
    # Get the latest position sizes
    position_data = get_latest_position_sizes(signals_dir, log_file)
    
    if position_data is None:
        log_message("No position data available - aborting cycle", log_file)
        return False
    
    # Get market regime data if available
    market_analysis = None
    if use_regime_detection:
        # Get latest regime data
        regime_data = get_latest_market_regimes(signals_dir, log_file)
        
        # Analyze market conditions
        if regime_data:
            market_analysis = analyze_market_conditions(position_data, regime_data, log_file)
    
    # Submit to broker
    if not submit_to_broker(position_data, market_analysis, log_file, dry_run):
        log_message("Failed to submit orders to broker - aborting cycle", log_file)
        return False
    
    log_message("Trading system cycle completed successfully", log_file)
    return True

def print_etf_help():
    """Print helpful information about using the system with ETFs."""
    help_text = """
=== ETF Integration Help ===

The trading system now supports ETFs alongside forex instruments. Here are some key points:

1. Dependencies:
   - yfinance (pip install yfinance)
   - pandas_ta (pip install pandas_ta)
   - numpy, pandas, and other standard libraries

2. Common Usage Commands:
   
   # Fetch ETF data manually:
   python rl/data/etf_data_ingestion.py --symbols SPY QQQ IWM GLD --period 5y --generate-features
   
   # Run trading system with ETF support:
   python run_trading_system.py --single-run --refresh-etf --dry-run
   
   # Run with adaptive position sizing and regime detection:
   python run_trading_system.py --refresh-etf --use-regime-detection --adapt-position-sizing --interval 60

3. Command Options:
   --refresh-etf: Refresh ETF data before each trading cycle
   --account-size: Specify account size in USD (default: 1000.0)
   --risk-percent: Maximum percentage of account to risk (default: 5.0)
   --interval: Minutes between trading cycles when running continuously (default: 60)
   --dry-run: Run in dry-run mode (no real orders)
   --single-run: Run once and exit
   --use-regime-detection: Use market regime detection
   --adapt-position-sizing: Use adaptive position sizing based on regimes

4. Troubleshooting:
   - If you encounter shape mismatch errors, the system will now automatically resize the feature vector
   - NaN handling for ETF data has been improved
   - Network issues with yfinance will be automatically retried
   - For detailed logs, check the log files in logs/ directory
"""
    print(help_text)

def main():
    """Main function to run the trading system on a schedule."""
    parser = argparse.ArgumentParser(description='Run the trading system on a schedule')
    parser.add_argument('--account-size', type=float, default=1000.0, help='Account size in USD')
    parser.add_argument('--risk-percent', type=float, default=5.0, help='Maximum percentage of account to risk daily')
    parser.add_argument('--model-path', type=str, default='models/rl_trader.pt', help='Path to the trained RL model')
    parser.add_argument('--interval', type=int, default=60, help='Interval in minutes between trading cycles')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no real orders)')
    parser.add_argument('--single-run', action='store_true', help='Run once and exit')
    parser.add_argument('--use-regime-detection', action='store_true', help='Use market regime detection')
    parser.add_argument('--adapt-position-sizing', action='store_true', help='Use adaptive position sizing')
    parser.add_argument('--refresh-etf', action='store_true', help='Refresh ETF data before each cycle')
    parser.add_argument('--help-etf', action='store_true', help='Show help for ETF integration')
    
    args = parser.parse_args()
    
    if args.help_etf:
        print_etf_help()
        return
    
    print("Starting Trading System Scheduler")
    print(f"Account Size: ${args.account_size}")
    print(f"Risk Percent: {args.risk_percent}%")
    print(f"Model Path: {args.model_path}")
    print(f"Interval: {args.interval} minutes")
    print(f"Dry Run: {args.dry_run}")
    print(f"Single Run: {args.single_run}")
    print(f"Market Regime Detection: {args.use_regime_detection}")
    print(f"Adaptive Position Sizing: {args.adapt_position_sizing}")
    print(f"Refresh ETF Data: {args.refresh_etf}")
    
    if args.single_run:
        print("\n=== Starting single trading cycle ===")
        run_trading_cycle(
            args.account_size, 
            args.risk_percent, 
            args.model_path, 
            args.use_regime_detection,
            args.adapt_position_sizing,
            args.refresh_etf,
            args.dry_run
        )
        return
    
    # Run on a schedule
    interval_minutes = args.interval  # Run every hour by default
    
    while True:
        try:
            print(f"\n=== Starting trading cycle at {datetime.datetime.now()} ===")
            run_trading_cycle(
                args.account_size, 
                args.risk_percent, 
                args.model_path, 
                args.use_regime_detection,
                args.adapt_position_sizing,
                args.refresh_etf,
                args.dry_run
            )
            
            # Calculate next run time
            next_run = datetime.datetime.now() + datetime.timedelta(minutes=interval_minutes)
            print(f"Next trading cycle scheduled for: {next_run}")
            
            # Sleep until next cycle
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            print("\nTrading system scheduler stopped by user")
            break
        except Exception as e:
            print(f"Error in trading cycle: {e}")
            print(traceback.format_exc())
            # Sleep for a shorter time if there was an error
            time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main() 