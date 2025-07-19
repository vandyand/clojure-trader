#!/usr/bin/env python3
import os
import sys
import logging
import torch
import numpy as np
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path to ensure imports work
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our feature adapter
from rl.data.feature_adapter import get_adapted_feature_vector
from rl.data.quick_etf_fetch import fetch_multiple_etfs, calculate_basic_features

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("quick_trade")

class SimplifiedTrader:
    """A simplified version of the RLTrader that only implements the essential functionality"""
    
    def __init__(self, model_path='models/rl_trader.pt'):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Define a simplified model structure (matches the real model)
        input_dim = 1084  # Expected input dimension
        hidden_dim = 256
        self.actor = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.LeakyReLU(),
            torch.nn.Linear(hidden_dim, hidden_dim // 2),
            torch.nn.LeakyReLU(),
            torch.nn.Linear(hidden_dim // 2, 20)  # 20 instruments
        ).to(self.device)
        
        # Load model
        self.load_model(model_path)
    
    def load_model(self, model_path):
        """Load the model from file"""
        try:
            if os.path.exists(model_path):
                logger.info(f"Loading model from {model_path}")
                state_dict = torch.load(model_path, map_location=self.device)
                self.actor.load_state_dict(state_dict['actor'])
                logger.info("Model loaded successfully")
            else:
                logger.warning(f"Model file {model_path} not found, using random weights")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.warning("Using random weights instead")
    
    def get_action(self, features):
        """Get trading action from feature vector"""
        with torch.no_grad():
            features_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
            action = self.actor(features_tensor)
            return action.squeeze().cpu().numpy()

def run_simplified_trading_system(model_path='models/rl_trader.pt'):
    """Run a simplified trading system"""
    logger.info("Starting simplified trading system")
    
    # Step 1: Fetch fresh ETF data
    logger.info("Fetching ETF data")
    etfs = ["SPY", "QQQ", "IWM", "GLD", "SLV", "VXX", "EEM", "XLF", "XLE"]
    etf_data = fetch_multiple_etfs(etfs, period="1mo")
    
    # Step 2: Create feature vector
    logger.info("Preparing feature vector")
    feature_vector = get_adapted_feature_vector()
    
    # Step 3: Create trader and get signals
    logger.info("Creating trader and generating signals")
    trader = SimplifiedTrader(model_path)
    signals = trader.get_action(feature_vector)
    
    # Step 4: Interpret signals
    logger.info("Interpreting signals")
    
    # In the real system, signals are mapped to specific forex pairs by index
    # Here we'll just use indices 0-4 for our ETFs (simplified)
    position_data = {
        "account_size": 10000.0,
        "risk_amount": 500.0,
        "positions": []
    }
    
    # Map signals to ETFs
    for i, symbol in enumerate(etfs):
        if i < len(signals):
            signal = signals[i]
            direction = "LONG" if signal > 0.1 else "SHORT" if signal < -0.1 else "NEUTRAL"
            strength = abs(signal)
            
            # Simple position sizing - just for demonstration
            position_size = int(5000 * strength) if strength > 0.1 else 0
            
            position_data["positions"].append({
                "instrument": symbol,
                "direction": direction,
                "position_size": float(position_size),
                "strength": float(strength),
                "usd_amount": float(position_size)
            })
    
    # Step 5: Save signals to file
    logger.info("Saving signals to file")
    os.makedirs("signals", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"signals/quick_signals_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(position_data, f, indent=2, default=str)
    
    logger.info(f"Trading signals saved to {filename}")
    
    # Print out signals
    logger.info("\n===== TRADING SIGNALS =====")
    logger.info(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Instrument   |   Direction   |   Signal Strength   |   Position Size")
    logger.info("--------------------------------------------------------------")
    
    for pos in position_data["positions"]:
        logger.info(f"{pos['instrument']:<12} | {pos['direction']:<12} | {pos['strength']:<18.4f} | ${pos['usd_amount']:<8.2f}")
    
    return position_data

if __name__ == "__main__":
    # Run the simplified trading system
    try:
        run_simplified_trading_system()
    except Exception as e:
        logger.error(f"Error running trading system: {e}", exc_info=True) 