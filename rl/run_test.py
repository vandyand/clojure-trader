import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import logging
from tqdm import tqdm
from typing import Dict, List, Tuple, Optional
import empyrical as ep

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

from rl.policy_network import RLTrader
from rl.constants import PAIRS_BY_LIQUIDITY_OANDA
from rl.data_fetcher import MarketDataFetcher
from rl.position_sizing import PositionSizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"backtest_results_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("backtest")

class BacktestEngine:
    """
    Comprehensive backtesting engine for evaluating RL trading strategies
    across different market conditions and time periods.
    """
    
    def __init__(self, 
                 model_path: str,
                 start_date: str, 
                 end_date: str,
                 account_size: float = 10000.0,
                 risk_percent: float = 5.0,
                 rebalance_frequency: str = 'D',
                 transaction_cost_bps: float = 2.0):
        """
        Initialize the backtesting engine
        
        Args:
            model_path: Path to the trained RL model
            start_date: Start date for backtesting in YYYY-MM-DD format
            end_date: End date for backtesting in YYYY-MM-DD format
            account_size: Initial account size in USD
            risk_percent: Maximum percentage of account to risk
            rebalance_frequency: Frequency to rebalance the portfolio ('D' for daily, 'W' for weekly)
            transaction_cost_bps: Transaction cost in basis points (2.0 = 0.02%)
        """
        self.model_path = model_path
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.initial_account_size = account_size
        self.risk_percent = risk_percent
        self.rebalance_frequency = rebalance_frequency
        self.transaction_cost_bps = transaction_cost_bps
        
        # Load model
        self.trader = RLTrader()
        try:
            self.trader.load_model(model_path)
            logger.info(f"Model loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
            
        # Initialize data fetcher
        self.data_fetcher = MarketDataFetcher(instruments=PAIRS_BY_LIQUIDITY_OANDA)
        
        # Initialize position sizer
        self.position_sizer = PositionSizer(account_size=account_size, risk_percent=risk_percent)
        
        # Results storage
        self.equity_curve = []
        self.daily_returns = []
        self.positions_history = []
        self.trade_history = []
        self.metrics = {}
        
    def _fetch_historical_data(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data for all instruments
        
        Returns:
            Dictionary mapping instrument to price DataFrame
        """
        logger.info("Fetching historical data for all instruments...")
        historical_data = {}
        
        for instrument in tqdm(PAIRS_BY_LIQUIDITY_OANDA):
            try:
                # Fetch candles from start to end date
                start_date_str = self.start_date.strftime("%Y-%m-%dT00:00:00Z")
                end_date_str = self.end_date.strftime("%Y-%m-%dT23:59:59Z")
                
                from api.oanda_api import get_candles
                candles = get_candles(instrument, self.rebalance_frequency, start_date_str, end_date_str)
                
                if not candles:
                    logger.warning(f"No candles returned for {instrument}")
                    continue
                    
                # Parse candles into DataFrame
                data = []
                for candle in candles:
                    timestamp = pd.to_datetime(candle["time"])
                    
                    # Extract OHLCV data
                    ohlc = candle["mid"] if "mid" in candle else candle["bid"]
                    row = {
                        "time": timestamp,
                        "open": float(ohlc["o"]),
                        "high": float(ohlc["h"]),
                        "low": float(ohlc["l"]),
                        "close": float(ohlc["c"]),
                        "volume": float(candle.get("volume", 0)),
                    }
                    data.append(row)
                
                # Create DataFrame
                df = pd.DataFrame(data)
                df.set_index("time", inplace=True)
                df.sort_index(inplace=True)
                
                historical_data[instrument] = df
                logger.info(f"Fetched {len(df)} candles for {instrument}")
                
            except Exception as e:
                logger.error(f"Error fetching data for {instrument}: {str(e)}")
                
        return historical_data
    
    def _calculate_features_for_date(self, historical_data: Dict[str, pd.DataFrame], 
                                    current_date: pd.Timestamp) -> Optional[np.ndarray]:
        """
        Calculate features for all instruments at a specific date
        
        Args:
            historical_data: Dictionary of historical price data
            current_date: The date to calculate features for
            
        Returns:
            Feature vector or None if features couldn't be calculated
        """
        # Make a copy of the data fetcher to avoid mutating the original
        temp_fetcher = MarketDataFetcher(instruments=PAIRS_BY_LIQUIDITY_OANDA)
        
        # Replace the price data cache with historical data up to the current date
        for instrument, df in historical_data.items():
            # Filter data up to current date
            historical_subset = df[df.index <= current_date].copy()
            if len(historical_subset) < 400:  # Need minimum history for feature calculation
                logger.warning(f"Not enough history for {instrument} at {current_date}")
                return None
                
            temp_fetcher.price_data_cache[instrument] = historical_subset
        
        # Calculate features for all instruments
        return temp_fetcher.prepare_feature_vector()
    
    def _get_next_prices(self, historical_data: Dict[str, pd.DataFrame], 
                        current_date: pd.Timestamp, next_date: pd.Timestamp) -> Dict[str, float]:
        """
        Get the price changes between current date and next date
        
        Args:
            historical_data: Dictionary of historical price data
            current_date: Current date
            next_date: Next date
            
        Returns:
            Dictionary of price changes by instrument
        """
        price_changes = {}
        
        for instrument, df in historical_data.items():
            if current_date not in df.index or next_date not in df.index:
                # Skip instruments with missing data
                continue
                
            current_price = df.loc[current_date, "close"]
            next_price = df.loc[next_date, "close"]
            
            price_changes[instrument] = next_price / current_price - 1.0
            
        return price_changes
    
    def _apply_transaction_costs(self, previous_positions: Dict[str, float], 
                               new_positions: Dict[str, float], 
                               current_prices: Dict[str, float]) -> float:
        """
        Calculate transaction costs from rebalancing
        
        Args:
            previous_positions: Previous position sizes
            new_positions: New position sizes
            current_prices: Current prices
            
        Returns:
            Total transaction cost in USD
        """
        total_cost = 0.0
        
        for instrument in set(previous_positions.keys()) | set(new_positions.keys()):
            prev_pos = previous_positions.get(instrument, 0.0)
            new_pos = new_positions.get(instrument, 0.0)
            
            if instrument in current_prices:
                # Calculate absolute change in position value
                price = current_prices[instrument]
                change_value = abs(new_pos - prev_pos) * price
                
                # Apply transaction cost
                cost = change_value * (self.transaction_cost_bps / 10000.0)
                total_cost += cost
        
        return total_cost
    
    def run_backtest(self) -> Dict[str, any]:
        """
        Run the backtest from start date to end date
        
        Returns:
            Dictionary of backtest results
        """
        logger.info(f"Starting backtest from {self.start_date} to {self.end_date}")
        
        # Fetch historical data
        historical_data = self._fetch_historical_data()
        
        if not historical_data:
            logger.error("No historical data fetched - aborting backtest")
            return {"success": False, "error": "No historical data available"}
        
        # Create a date range for rebalancing
        if self.rebalance_frequency == 'D':
            rebalance_dates = pd.date_range(start=self.start_date, end=self.end_date, freq='B')  # Business days
        elif self.rebalance_frequency == 'W':
            rebalance_dates = pd.date_range(start=self.start_date, end=self.end_date, freq='W-FRI')  # Weekly on Friday
        else:
            raise ValueError(f"Unsupported rebalance frequency: {self.rebalance_frequency}")
        
        # Filter to only include dates in the data
        valid_dates = []
        for instrument, df in historical_data.items():
            valid_dates.extend(df.index.tolist())
        valid_dates = sorted(set(valid_dates))
        
        rebalance_dates = [date for date in rebalance_dates if date in valid_dates]
        
        # Initialize account and positions
        account_value = self.initial_account_size
        positions = {instrument: 0.0 for instrument in PAIRS_BY_LIQUIDITY_OANDA}
        usd_values = {instrument: 0.0 for instrument in PAIRS_BY_LIQUIDITY_OANDA}
        
        self.equity_curve = [(self.start_date, account_value)]
        previous_date = None
        
        # Run the backtest
        logger.info(f"Running backtest over {len(rebalance_dates)} rebalance dates...")
        
        for i, current_date in enumerate(tqdm(rebalance_dates)):
            try:
                # Get next rebalance date
                next_date = rebalance_dates[i+1] if i+1 < len(rebalance_dates) else None
                if next_date is None:
                    break
                
                # Calculate features at current date
                feature_vector = self._calculate_features_for_date(historical_data, current_date)
                
                if feature_vector is None:
                    logger.warning(f"Skipping date {current_date} - unable to calculate features")
                    continue
                
                # Convert to tensor
                feature_tensor = torch.tensor(feature_vector, dtype=torch.float32).unsqueeze(0).to(self.trader.device)
                
                # Generate positions with the RL model
                with torch.no_grad():
                    action, _ = self.trader.get_action(feature_tensor, training=False)
                
                raw_positions = action[0].cpu().numpy()
                
                # Format trading signals
                signals = []
                for i, instr in enumerate(PAIRS_BY_LIQUIDITY_OANDA):
                    if i < len(raw_positions):  # Ensure we have position data
                        pos = raw_positions[i]
                        direction = "LONG" if pos > 0.1 else "SHORT" if pos < -0.1 else "NEUTRAL"
                        strength = abs(pos)
                        
                        signals.append({
                            "instrument": instr,
                            "position": float(pos),
                            "direction": direction,
                            "strength": float(strength)
                        })
                
                # Calculate position sizes
                self.position_sizer.account_size = account_value  # Update account size
                position_data = self.position_sizer.convert_signals_to_positions(signals)
                
                # Extract new positions
                new_positions = {pos["instrument"]: pos["position_size"] for pos in position_data["positions"]}
                new_usd_values = {pos["instrument"]: pos["usd_amount"] for pos in position_data["positions"]}
                
                # Get current prices
                current_prices = {}
                for instrument, df in historical_data.items():
                    if current_date in df.index:
                        current_prices[instrument] = df.loc[current_date, "close"]
                
                # Calculate transaction costs if we have previous positions
                transaction_cost = 0.0
                if previous_date is not None:
                    transaction_cost = self._apply_transaction_costs(positions, new_positions, current_prices)
                    account_value -= transaction_cost
                
                # Update positions
                positions = new_positions
                usd_values = new_usd_values
                
                # Get price changes to next rebalance date
                price_changes = self._get_next_prices(historical_data, current_date, next_date)
                
                # Calculate P&L
                pnl = 0.0
                for instrument, position in positions.items():
                    if instrument in price_changes:
                        # Calculate P&L for this instrument
                        instrument_pnl = usd_values[instrument] * price_changes[instrument]
                        pnl += instrument_pnl
                
                # Update account value
                account_value += pnl
                
                # Record equity and positions
                self.equity_curve.append((next_date, account_value))
                self.positions_history.append({
                    "date": current_date,
                    "positions": positions.copy(),
                    "usd_values": usd_values.copy(),
                    "account_value": account_value
                })
                
                # Record trade
                if previous_date is not None:
                    self.trade_history.append({
                        "start_date": previous_date,
                        "end_date": current_date,
                        "pnl": pnl,
                        "transaction_cost": transaction_cost,
                        "return": pnl / (account_value - pnl)
                    })
                    
                    # Record daily return
                    self.daily_returns.append(pnl / (account_value - pnl))
                
                previous_date = current_date
                
            except Exception as e:
                logger.error(f"Error at date {current_date}: {str(e)}", exc_info=True)
                continue
        
        # Calculate performance metrics
        self._calculate_metrics()
        
        logger.info(f"Backtest completed. Final account value: ${account_value:.2f}")
        logger.info(f"Total return: {(account_value / self.initial_account_size - 1.0) * 100:.2f}%")
        
        return self.get_results()
    
    def _calculate_metrics(self):
        """Calculate performance metrics from backtest results"""
        if not self.daily_returns:
            logger.warning("No trade history to calculate metrics from")
            return
        
        returns_series = pd.Series(self.daily_returns)
        
        # Basic metrics
        self.metrics = {
            "total_return": (self.equity_curve[-1][1] / self.initial_account_size) - 1.0,
            "annual_return": ep.annual_return(returns_series, annualization=252),
            "annual_volatility": ep.annual_volatility(returns_series, period='daily', annualization=252),
            "sharpe_ratio": ep.sharpe_ratio(returns_series, risk_free=0.0, annualization=252),
            "sortino_ratio": ep.sortino_ratio(returns_series, required_return=0.0, annualization=252),
            "max_drawdown": ep.max_drawdown(returns_series),
            "calmar_ratio": ep.calmar_ratio(returns_series, annualization=252),
            "stability": ep.stability_of_timeseries(returns_series),
            "value_at_risk": returns_series.quantile(0.05),  # 5% VaR
            "expected_shortfall": returns_series[returns_series <= returns_series.quantile(0.05)].mean(),
            "positive_returns": (returns_series > 0).mean(),
            "profit_factor": abs(returns_series[returns_series > 0].sum() / returns_series[returns_series < 0].sum()) if (returns_series < 0).any() else float('inf'),
            "trade_count": len(self.trade_history),
        }
        
        logger.info("\n=== PERFORMANCE METRICS ===")
        for key, value in self.metrics.items():
            logger.info(f"{key}: {value:.6f}")
    
    def plot_equity_curve(self, save_path=None):
        """Plot equity curve from backtest results"""
        if not self.equity_curve:
            logger.warning("No equity curve to plot")
            return
        
        dates = [entry[0] for entry in self.equity_curve]
        values = [entry[1] for entry in self.equity_curve]
        
        plt.figure(figsize=(14, 7))
        plt.plot(dates, values)
        plt.title(f"Equity Curve ({self.start_date.date()} to {self.end_date.date()})")
        plt.xlabel("Date")
        plt.ylabel("Account Value ($)")
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Equity curve saved to {save_path}")
        else:
            plt.show()
    
    def plot_drawdowns(self, save_path=None):
        """Plot drawdowns from equity curve"""
        if not self.equity_curve:
            logger.warning("No equity curve to plot drawdowns")
            return
        
        dates = [entry[0] for entry in self.equity_curve]
        values = np.array([entry[1] for entry in self.equity_curve])
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max
        
        plt.figure(figsize=(14, 7))
        plt.plot(dates, drawdowns * 100)
        plt.title(f"Drawdowns ({self.start_date.date()} to {self.end_date.date()})")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Drawdowns plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_position_allocations(self, save_path=None):
        """Plot position allocations over time"""
        if not self.positions_history:
            logger.warning("No position history to plot allocations")
            return
        
        # Extract dates and usd_values
        dates = [entry["date"] for entry in self.positions_history]
        
        # Create DataFrame with USD allocations
        allocations = {}
        for entry in self.positions_history:
            for instrument, usd_value in entry["usd_values"].items():
                if instrument not in allocations:
                    allocations[instrument] = []
                allocations[instrument].append(usd_value / entry["account_value"])
        
        # Filter to only include instruments with non-zero allocations
        active_instruments = [instr for instr, values in allocations.items() 
                             if max(abs(val) for val in values) > 0.01]
        
        # Plot
        plt.figure(figsize=(14, 10))
        for instrument in active_instruments:
            plt.plot(dates, allocations[instrument], label=instrument)
        
        plt.title(f"Position Allocations ({self.start_date.date()} to {self.end_date.date()})")
        plt.xlabel("Date")
        plt.ylabel("% of Portfolio")
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        plt.grid(True)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Position allocations plot saved to {save_path}")
        else:
            plt.show()
    
    def get_results(self) -> Dict[str, any]:
        """
        Get complete backtest results
        
        Returns:
            Dictionary with all backtest results
        """
        return {
            "success": True,
            "initial_account_size": self.initial_account_size,
            "final_account_value": self.equity_curve[-1][1] if self.equity_curve else self.initial_account_size,
            "equity_curve": self.equity_curve,
            "metrics": self.metrics,
            "positions_history": self.positions_history,
            "trade_history": self.trade_history,
            "config": {
                "start_date": self.start_date,
                "end_date": self.end_date,
                "risk_percent": self.risk_percent,
                "rebalance_frequency": self.rebalance_frequency,
                "transaction_cost_bps": self.transaction_cost_bps,
                "model_path": self.model_path
            }
        }
        
def main():
    """Parse command line arguments and run backtest"""
    parser = argparse.ArgumentParser(description='Backtest RL trading strategy')
    parser.add_argument('--start-date', type=str, required=True, help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--account-size', type=float, default=10000.0, help='Initial account size in USD')
    parser.add_argument('--risk-percent', type=float, default=5.0, help='Maximum percentage of account to risk')
    parser.add_argument('--model-path', type=str, default='models/rl_trader.pt', help='Path to the trained RL model')
    parser.add_argument('--rebalance-frequency', type=str, default='D', choices=['D', 'W'], help='Rebalancing frequency (D=daily, W=weekly)')
    parser.add_argument('--transaction-cost-bps', type=float, default=2.0, help='Transaction cost in basis points')
    parser.add_argument('--output-dir', type=str, default='backtest_results', help='Directory to save results')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run backtest
    backtest = BacktestEngine(
        model_path=args.model_path,
        start_date=args.start_date,
        end_date=args.end_date,
        account_size=args.account_size,
        risk_percent=args.risk_percent,
        rebalance_frequency=args.rebalance_frequency,
        transaction_cost_bps=args.transaction_cost_bps
    )
    
    results = backtest.run_backtest()
    
    if results["success"]:
        # Save plots
        backtest.plot_equity_curve(save_path=os.path.join(args.output_dir, "equity_curve.png"))
        backtest.plot_drawdowns(save_path=os.path.join(args.output_dir, "drawdowns.png"))
        backtest.plot_position_allocations(save_path=os.path.join(args.output_dir, "position_allocations.png"))
        
        # Save results to JSON
        import json
        result_path = os.path.join(args.output_dir, f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # Convert dates to strings for JSON serialization
        serializable_results = results.copy()
        serializable_results["equity_curve"] = [(dt.strftime('%Y-%m-%d'), val) for dt, val in results["equity_curve"]]
        
        for entry in serializable_results["positions_history"]:
            entry["date"] = entry["date"].strftime('%Y-%m-%d')
            
        for entry in serializable_results["trade_history"]:
            entry["start_date"] = entry["start_date"].strftime('%Y-%m-%d')
            entry["end_date"] = entry["end_date"].strftime('%Y-%m-%d')
            
        serializable_results["config"]["start_date"] = serializable_results["config"]["start_date"].strftime('%Y-%m-%d')
        serializable_results["config"]["end_date"] = serializable_results["config"]["end_date"].strftime('%Y-%m-%d')
        
        with open(result_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Backtest results saved to {result_path}")
    else:
        logger.error(f"Backtest failed: {results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main() 