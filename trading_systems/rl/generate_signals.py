import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import torch
from datetime import datetime
import json
import argparse
import logging

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from rl.policy_network import RLTrader
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data_fetcher import MarketDataFetcher
from rl.position_sizing import PositionSizer
from rl.market_regime import MarketRegimeDetector, AdaptivePositionSizer, calculate_volatilities

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"generate_signals_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("generate_signals")

def generate_trading_signals(account_size=1000.0, risk_percent=5.0, model_path='models/rl_trader.pt', 
                            use_regime_detection=True, adapt_position_sizing=True):
    """
    Generate trading signals from the latest market data and convert to position sizes
    
    Args:
        account_size: Total account size in USD
        risk_percent: Maximum percentage of account to risk daily
        model_path: Path to the trained RL model
        use_regime_detection: Whether to use market regime detection
        adapt_position_sizing: Whether to adapt position sizing based on regimes
    
    Returns:
        Dictionary with trading signals and position sizes
    """
    logger.info("Starting trading signal generation")
    
    # Create RL trader and load model
    trader = RLTrader(actor_lr=1e-4, critic_lr=1e-3, gamma=0.99, entropy_weight=0.01)
    
    # Try to load the trained model
    try:
        logger.info(f"Loading trained model from {model_path}")
        trader.load_model(model_path)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Error: Could not load model: {e}")
        return None
    
    try:
        # Create data fetcher for latest market data
        data_fetcher = MarketDataFetcher(instruments=PAIRS_BY_LIQUIDITY_OANDA)
        
        # Get feature vector for all instruments
        logger.info("Fetching latest market data and calculating features")
        feature_vector = data_fetcher.prepare_feature_vector()
        
        if feature_vector is None:
            logger.error("Failed to create feature vector")
            return None
        
        # Convert to tensor
        feature_tensor = torch.tensor(feature_vector, dtype=torch.float32).unsqueeze(0).to(trader.device)
        
        # Generate positions with the RL model
        logger.info("Generating trading signals with RL model")
        with torch.no_grad():
            action, _ = trader.get_action(feature_tensor, training=False)
        
        positions = action[0].cpu().numpy()
        
        # Format trading signals
        signals = []
        logger.info("\n===== TRADING SIGNALS =====")
        logger.info(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("Instrument   |   Direction   |   Raw Signal")
        logger.info("------------------------------------------")
        
        for i, instr in enumerate(PAIRS_BY_LIQUIDITY_OANDA):
            if i < len(positions):  # Ensure we have position data
                pos = positions[i]
                direction = "LONG" if pos > 0.1 else "SHORT" if pos < -0.1 else "NEUTRAL"
                strength = abs(pos)
                logger.info(f"{instr:<12} | {direction:<12} | {strength:.4f}")
                
                signals.append({
                    "instrument": instr,
                    "position": float(pos),
                    "direction": direction,
                    "strength": float(strength)
                })

        # Market regime detection and adaptive position sizing
        if use_regime_detection:
            logger.info("\n===== MARKET REGIME DETECTION =====")
            
            # Initialize regime detector
            regime_detector = MarketRegimeDetector(window_size=60, n_regimes=3)
            
            # Process each instrument to detect market regime
            regime_infos = {}
            price_data = {}
            
            for instrument in PAIRS_BY_LIQUIDITY_OANDA:
                try:
                    # Get price data from data fetcher cache
                    if instrument in data_fetcher.price_data_cache:
                        df = data_fetcher.price_data_cache[instrument]
                        price_data[instrument] = df
                        
                        # Detect regime
                        regime_info = regime_detector.detect_regime(instrument, df, method='ensemble')
                        regime_infos[instrument] = regime_info
                        
                        logger.info(f"{instrument}: {regime_info['regime_name']} regime (confidence: {regime_info['confidence']:.2f})")
                except Exception as e:
                    logger.error(f"Error detecting regime for {instrument}: {e}")
            
            # Calculate volatilities
            if price_data:
                volatilities = calculate_volatilities(price_data)
                logger.info(f"Calculated volatilities for {len(volatilities)} instruments")
            else:
                volatilities = None
                logger.warning("No price data available for volatility calculation")
            
            # Save regime information
            regime_output_dir = "signals/regimes"
            os.makedirs(regime_output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            regime_path = os.path.join(regime_output_dir, f"regimes_{timestamp}.json")
            
            with open(regime_path, 'w') as f:
                # Convert datetime objects to strings
                serializable_regimes = {}
                for instr, regime in regime_infos.items():
                    serializable_regime = regime.copy()
                    serializable_regime['timestamp'] = serializable_regime['timestamp'].isoformat()
                    serializable_regimes[instr] = serializable_regime
                
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "regimes": serializable_regimes,
                    "volatilities": {k: float(v) for k, v in volatilities.items()} if volatilities else {}
                }, f, indent=2)
            
            logger.info(f"Market regime analysis saved to {regime_path}")
        
        # Calculate actual position sizes
        logger.info("\nCalculating position sizes...")
        
        if use_regime_detection and adapt_position_sizing:
            # Use adaptive position sizer
            adaptive_sizer = AdaptivePositionSizer(
                base_account_size=account_size, 
                base_risk_percent=risk_percent,
                max_risk_percent=risk_percent * 1.5,  # Allow up to 50% more risk in favorable regimes
                min_risk_percent=risk_percent * 0.5,  # Reduce risk to 50% in unfavorable regimes
                volatility_adjustment=True
            )
            
            # Standard position sizing first
            position_sizer = PositionSizer(account_size=account_size, risk_percent=risk_percent)
            position_sizes = position_sizer.convert_signals_to_positions(signals)
            
            # Then adapt based on regimes
            if 'positions' in position_sizes and regime_infos:
                logger.info("Applying adaptive position sizing based on market regimes")
                
                # Adapt positions
                adapted_positions = adaptive_sizer.adjust_position_sizes(
                    position_sizes['positions'], 
                    regime_infos,
                    volatilities
                )
                
                # Replace with adapted positions
                position_sizes['positions'] = adapted_positions
                position_sizes['adaptive_sizing'] = True
                position_sizes['risk_percent'] = adaptive_sizer.current_risk_percent
                
                logger.info(f"Risk percent adjusted from {risk_percent}% to {adaptive_sizer.current_risk_percent:.2f}%")
        else:
            # Use standard position sizer
            position_sizer = PositionSizer(account_size=account_size, risk_percent=risk_percent)
            position_sizes = position_sizer.convert_signals_to_positions(signals)
        
        # Save signals and position sizes to files
        output_dir = "signals"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save raw signals
        signals_path = os.path.join(output_dir, f"trading_signals_{timestamp}.json")
        with open(signals_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "signals": signals
            }, f, indent=2)
            
        # Save position sizes
        positions_path = os.path.join(output_dir, f"position_sizes_{timestamp}.json")
        with open(positions_path, 'w') as f:
            json.dump(position_sizes, f, indent=2)
            
        logger.info(f"\nTrading signals saved to {signals_path}")
        logger.info(f"Position sizes saved to {positions_path}")
        
        # Display position sizes
        logger.info("\n===== POSITION SIZES =====")
        logger.info(f"Account size: ${position_sizes['account_size']:.2f}")
        logger.info(f"Risk amount: ${position_sizes['total_allocation']:.2f}")
        
        if use_regime_detection and adapt_position_sizing:
            logger.info(f"Adaptive sizing: Yes (Risk {position_sizes['risk_percent']:.2f}%)")
        
        logger.info("\nInstrument   |   Direction   |   Position Size   |   USD Amount")
        logger.info("--------------------------------------------------------------")
        
        for instrument, pos in position_sizes["positions"].items():
            instrument_info = f"{instrument:<12} | {pos['direction']:<12} | {pos['size']:<16.6f} | ${pos['size']:<8.2f}"
            logger.info(instrument_info)
        
        return position_sizes
        
    except Exception as e:
        logger.error(f"Error generating trading signals: {e}", exc_info=True)
        return None

def main():
    """Parse command line arguments and generate trading signals"""
    parser = argparse.ArgumentParser(description='Generate trading signals and position sizes')
    parser.add_argument('--account-size', type=float, default=1000.0, help='Account size in USD')
    parser.add_argument('--risk-percent', type=float, default=5.0, help='Maximum percentage of account to risk daily')
    parser.add_argument('--model-path', type=str, default='models/rl_trader.pt', help='Path to the trained RL model')
    parser.add_argument('--use-regime-detection', action='store_true', help='Use market regime detection')
    parser.add_argument('--adapt-position-sizing', action='store_true', help='Use adaptive position sizing')
    
    args = parser.parse_args()
    
    # Generate trading signals
    generate_trading_signals(
        account_size=args.account_size,
        risk_percent=args.risk_percent,
        model_path=args.model_path,
        use_regime_detection=args.use_regime_detection,
        adapt_position_sizing=args.adapt_position_sizing
    )

if __name__ == "__main__":
    main() 