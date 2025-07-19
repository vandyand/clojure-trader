#!/usr/bin/env python
"""
Diagnostic script for the RL trading system to assess current state and identify issues.
This script will check all components of the multi-instrument RL workflow:
1. Feature engineering and grid search
2. Feature pruning 
3. Autoencoder training and loading
4. RL policy network
5. Custom reward function
6. 20 forex instrument integration
"""
import os
import sys
import torch
import numpy as np
import pandas as pd
from pathlib import Path
import psycopg2
import json
from datetime import datetime
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.constants import PAIRS_BY_LIQUIDITY_OANDA, ETF_SYMBOLS
from rl.policy_network import RLTrader, FusionAutoencoder, RewardCalculator
from rl.data.autoencoder_fusion import get_selected_features_per_instrument, load_instrument_data
from rl.data.feature_pruning import get_forex_instruments, get_etf_instruments

class RLSystemDiagnostic:
    """Comprehensive diagnostic for the RL trading system."""
    
    def __init__(self):
        self.results = {
            'database_connection': False,
            'feature_engineering': {},
            'feature_pruning': {},
            'autoencoder': {},
            'policy_network': {},
            'reward_function': {},
            'data_loading': {},
            'overall_status': 'UNKNOWN'
        }
        
    def run_full_diagnostic(self):
        """Run complete diagnostic of the RL system."""
        print("=" * 80)
        print("RL TRADING SYSTEM DIAGNOSTIC")
        print("=" * 80)
        print(f"Timestamp: {datetime.now()}")
        print()
        
        # 1. Database Connection Test
        self._test_database_connection()
        
        # 2. Feature Engineering Assessment
        self._test_feature_engineering()
        
        # 3. Feature Pruning Assessment
        self._test_feature_pruning()
        
        # 4. Autoencoder Assessment
        self._test_autoencoder()
        
        # 5. Policy Network Assessment
        self._test_policy_network()
        
        # 6. Reward Function Assessment
        self._test_reward_function()
        
        # 7. Data Loading Assessment
        self._test_data_loading()
        
        # 8. Overall System Assessment
        self._assess_overall_status()
        
        # 9. Generate Report
        self._generate_report()
        
    def _test_database_connection(self):
        """Test database connectivity and basic setup."""
        print("1. DATABASE CONNECTION TEST")
        print("-" * 40)
        
        try:
            # Test basic connection
            conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'rl_forex'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
            
            # Test required tables exist
            with conn.cursor() as cur:
                # Check forex_features table
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'forex_features'
                """)
                forex_table_exists = cur.fetchone()[0] > 0
                
                # Check etf_features table
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'etf_features'
                """)
                etf_table_exists = cur.fetchone()[0] > 0
                
                # Check selected_features_per_instrument table
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'selected_features_per_instrument'
                """)
                selected_features_table_exists = cur.fetchone()[0] > 0
                
                # Count instruments in forex_features
                cur.execute("SELECT COUNT(DISTINCT instrument) FROM forex_features")
                forex_instrument_count = cur.fetchone()[0]
                
                # Count instruments in etf_features
                cur.execute("SELECT COUNT(DISTINCT instrument) FROM etf_features")
                etf_instrument_count = cur.fetchone()[0]
            
            conn.close()
            
            self.results['database_connection'] = {
                'status': 'SUCCESS',
                'forex_table_exists': forex_table_exists,
                'etf_table_exists': etf_table_exists,
                'selected_features_table_exists': selected_features_table_exists,
                'forex_instrument_count': forex_instrument_count,
                'etf_instrument_count': etf_instrument_count
            }
            
            print(f"✓ Database connection successful")
            print(f"  - Forex features table: {'✓' if forex_table_exists else '✗'}")
            print(f"  - ETF features table: {'✓' if etf_table_exists else '✗'}")
            print(f"  - Selected features table: {'✓' if selected_features_table_exists else '✗'}")
            print(f"  - Forex instruments: {forex_instrument_count}")
            print(f"  - ETF instruments: {etf_instrument_count}")
            
        except Exception as e:
            self.results['database_connection'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Database connection failed: {e}")
        
        print()
    
    def _test_feature_engineering(self):
        """Test feature engineering components."""
        print("2. FEATURE ENGINEERING ASSESSMENT")
        print("-" * 40)
        
        try:
            # Test feature selection per instrument
            instrument_features = get_selected_features_per_instrument()
            
            # Check if we have features for all 20 forex pairs
            forex_pairs_with_features = []
            for pair in PAIRS_BY_LIQUIDITY_OANDA:
                if pair in instrument_features:
                    feature_count = len(instrument_features[pair])
                    forex_pairs_with_features.append((pair, feature_count))
                else:
                    forex_pairs_with_features.append((pair, 0))
            
            # Check ETF features
            etf_symbols_with_features = []
            for symbol in ETF_SYMBOLS:
                if symbol in instrument_features:
                    feature_count = len(instrument_features[symbol])
                    etf_symbols_with_features.append((symbol, feature_count))
                else:
                    etf_symbols_with_features.append((symbol, 0))
            
            self.results['feature_engineering'] = {
                'status': 'SUCCESS',
                'total_instruments': len(instrument_features),
                'forex_pairs_with_features': forex_pairs_with_features,
                'etf_symbols_with_features': etf_symbols_with_features,
                'expected_forex_pairs': len(PAIRS_BY_LIQUIDITY_OANDA),
                'expected_etf_symbols': len(ETF_SYMBOLS)
            }
            
            print(f"✓ Feature engineering data available")
            print(f"  - Total instruments with features: {len(instrument_features)}")
            print(f"  - Forex pairs with features: {sum(1 for _, count in forex_pairs_with_features if count > 0)}/{len(PAIRS_BY_LIQUIDITY_OANDA)}")
            print(f"  - ETF symbols with features: {sum(1 for _, count in etf_symbols_with_features if count > 0)}/{len(ETF_SYMBOLS)}")
            
            # Show missing forex pairs
            missing_forex = [pair for pair, count in forex_pairs_with_features if count == 0]
            if missing_forex:
                print(f"  - Missing forex pairs: {missing_forex}")
            
        except Exception as e:
            self.results['feature_engineering'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Feature engineering failed: {e}")
        
        print()
    
    def _test_feature_pruning(self):
        """Test feature pruning functionality."""
        print("3. FEATURE PRUNING ASSESSMENT")
        print("-" * 40)
        
        try:
            # Test getting forex instruments from database
            forex_instruments = get_forex_instruments()
            etf_instruments = get_etf_instruments()
            
            # Check if pruning has been done
            conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'rl_forex'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
            
            with conn.cursor() as cur:
                # Check how many instruments have been pruned
                cur.execute("""
                    SELECT instrument, COUNT(*) as feature_count 
                    FROM selected_features_per_instrument 
                    GROUP BY instrument 
                    HAVING COUNT(*) >= 20
                    ORDER BY feature_count DESC
                """)
                pruned_instruments = cur.fetchall()
            
            conn.close()
            
            self.results['feature_pruning'] = {
                'status': 'SUCCESS',
                'forex_instruments_in_db': len(forex_instruments),
                'etf_instruments_in_db': len(etf_instruments),
                'pruned_instruments': pruned_instruments,
                'pruned_count': len(pruned_instruments)
            }
            
            print(f"✓ Feature pruning data available")
            print(f"  - Forex instruments in DB: {len(forex_instruments)}")
            print(f"  - ETF instruments in DB: {len(etf_instruments)}")
            print(f"  - Instruments with pruned features: {len(pruned_instruments)}")
            
            # Show top pruned instruments
            if pruned_instruments:
                print(f"  - Top pruned instruments:")
                for instrument, count in pruned_instruments[:5]:
                    print(f"    {instrument}: {count} features")
            
        except Exception as e:
            self.results['feature_pruning'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Feature pruning failed: {e}")
        
        print()
    
    def _test_autoencoder(self):
        """Test autoencoder functionality."""
        print("4. AUTOENCODER ASSESSMENT")
        print("-" * 40)
        
        try:
            # Check for autoencoder model files
            models_dir = Path(__file__).parent / ".." / "models"
            autoencoder_files = {
                'fusion_autoencoder.pt': models_dir / "fusion_autoencoder.pt",
                'autoencoder_fx.pt': models_dir / "autoencoder_fx.pt",
                'autoencoder_etf.pt': models_dir / "autoencoder_etf.pt",
                'autoencoder_unified.pt': models_dir / "autoencoder_unified.pt"
            }
            
            existing_models = {}
            for name, path in autoencoder_files.items():
                if path.exists():
                    size_mb = path.stat().st_size / (1024 * 1024)
                    existing_models[name] = {
                        'path': str(path),
                        'size_mb': size_mb,
                        'exists': True
                    }
                else:
                    existing_models[name] = {
                        'path': str(path),
                        'exists': False
                    }
            
            # Try to load the fusion autoencoder
            fusion_autoencoder_loaded = False
            autoencoder_error = None
            try:
                autoencoder = FusionAutoencoder()
                fusion_autoencoder_loaded = True
                bottleneck_dim = autoencoder.bottleneck_dim
            except Exception as e:
                autoencoder_error = str(e)
                bottleneck_dim = None
            
            self.results['autoencoder'] = {
                'status': 'SUCCESS' if fusion_autoencoder_loaded else 'FAILED',
                'existing_models': existing_models,
                'fusion_autoencoder_loaded': fusion_autoencoder_loaded,
                'bottleneck_dim': bottleneck_dim,
                'error': autoencoder_error
            }
            
            print(f"✓ Autoencoder assessment complete")
            print(f"  - Fusion autoencoder loaded: {'✓' if fusion_autoencoder_loaded else '✗'}")
            if fusion_autoencoder_loaded:
                print(f"  - Bottleneck dimension: {bottleneck_dim}")
            
            print(f"  - Available model files:")
            for name, info in existing_models.items():
                status = "✓" if info['exists'] else "✗"
                size_info = f" ({info['size_mb']:.1f}MB)" if info['exists'] else ""
                print(f"    {status} {name}{size_info}")
            
            if autoencoder_error:
                print(f"  - Error loading fusion autoencoder: {autoencoder_error}")
            
        except Exception as e:
            self.results['autoencoder'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Autoencoder assessment failed: {e}")
        
        print()
    
    def _test_policy_network(self):
        """Test policy network functionality."""
        print("5. POLICY NETWORK ASSESSMENT")
        print("-" * 40)
        
        try:
            # Try to initialize RL trader
            trader_initialized = False
            trader_error = None
            try:
                trader = RLTrader()
                trader_initialized = True
                n_instruments = trader.n_instruments
                state_dim = trader.state_dim
            except Exception as e:
                trader_error = str(e)
                n_instruments = None
                state_dim = None
            
            # Check for policy model files
            models_dir = Path(__file__).parent / ".." / "models"
            policy_files = {
                'rl_trader.pt': models_dir / "rl_trader.pt",
                'best_policy.pt': models_dir / "best_policy.pt",
                'rl_policy.pt': models_dir / "rl_policy.pt"
            }
            
            existing_policies = {}
            for name, path in policy_files.items():
                if path.exists():
                    size_mb = path.stat().st_size / (1024 * 1024)
                    existing_policies[name] = {
                        'path': str(path),
                        'size_mb': size_mb,
                        'exists': True
                    }
                else:
                    existing_policies[name] = {
                        'path': str(path),
                        'exists': False
                    }
            
            self.results['policy_network'] = {
                'status': 'SUCCESS' if trader_initialized else 'FAILED',
                'trader_initialized': trader_initialized,
                'n_instruments': n_instruments,
                'state_dim': state_dim,
                'existing_policies': existing_policies,
                'error': trader_error
            }
            
            print(f"✓ Policy network assessment complete")
            print(f"  - RL trader initialized: {'✓' if trader_initialized else '✗'}")
            if trader_initialized:
                print(f"  - Number of instruments: {n_instruments}")
                print(f"  - State dimension: {state_dim}")
            
            print(f"  - Available policy files:")
            for name, info in existing_policies.items():
                status = "✓" if info['exists'] else "✗"
                size_info = f" ({info['size_mb']:.1f}MB)" if info['exists'] else ""
                print(f"    {status} {name}{size_info}")
            
            if trader_error:
                print(f"  - Error initializing trader: {trader_error}")
            
        except Exception as e:
            self.results['policy_network'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Policy network assessment failed: {e}")
        
        print()
    
    def _test_reward_function(self):
        """Test reward function functionality."""
        print("6. REWARD FUNCTION ASSESSMENT")
        print("-" * 40)
        
        try:
            # Test reward calculator
            reward_calc = RewardCalculator()
            
            # Test with sample data
            sample_outputs = np.array([0.5, -0.3, 0.2, -0.1, 0.4])
            sample_price_changes = np.array([0.01, -0.005, 0.008, -0.003, 0.006])
            
            reward_info = reward_calc.calculate_reward(sample_outputs, sample_price_changes)
            
            self.results['reward_function'] = {
                'status': 'SUCCESS',
                'reward_calculator_initialized': True,
                'sample_reward': reward_info['final_reward'],
                'sample_portfolio_return': reward_info['portfolio_return'],
                'sample_entropy': reward_info['position_entropy'],
                'sample_confidence': reward_info['confidence_weight']
            }
            
            print(f"✓ Reward function working")
            print(f"  - Sample reward: {reward_info['final_reward']:.6f}")
            print(f"  - Sample portfolio return: {reward_info['portfolio_return']:.6f}")
            print(f"  - Sample entropy: {reward_info['position_entropy']:.6f}")
            print(f"  - Sample confidence: {reward_info['confidence_weight']:.6f}")
            
        except Exception as e:
            self.results['reward_function'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Reward function failed: {e}")
        
        print()
    
    def _test_data_loading(self):
        """Test data loading functionality."""
        print("7. DATA LOADING ASSESSMENT")
        print("-" * 40)
        
        try:
            # Test loading forex data
            forex_data_loaded = False
            forex_error = None
            try:
                forex_data, forex_features = load_instrument_data(
                    target_instruments=PAIRS_BY_LIQUIDITY_OANDA[:5],  # Test with first 5 pairs
                    instrument_feature_map=get_selected_features_per_instrument(),
                    table_name='forex_features',
                    n_rows=1000
                )
                forex_data_loaded = True
                forex_shape = forex_data.shape if forex_data is not None else None
            except Exception as e:
                forex_error = str(e)
                forex_shape = None
            
            # Test loading ETF data
            etf_data_loaded = False
            etf_error = None
            try:
                etf_data, etf_features = load_instrument_data(
                    target_instruments=ETF_SYMBOLS[:5],  # Test with first 5 symbols
                    instrument_feature_map=get_selected_features_per_instrument(),
                    table_name='etf_features',
                    n_rows=1000
                )
                etf_data_loaded = True
                etf_shape = etf_data.shape if etf_data is not None else None
            except Exception as e:
                etf_error = str(e)
                etf_shape = None
            
            self.results['data_loading'] = {
                'status': 'SUCCESS' if (forex_data_loaded or etf_data_loaded) else 'FAILED',
                'forex_data_loaded': forex_data_loaded,
                'forex_data_shape': forex_shape,
                'forex_error': forex_error,
                'etf_data_loaded': etf_data_loaded,
                'etf_data_shape': etf_shape,
                'etf_error': etf_error
            }
            
            print(f"✓ Data loading assessment complete")
            print(f"  - Forex data loaded: {'✓' if forex_data_loaded else '✗'}")
            if forex_data_loaded and forex_shape:
                print(f"    Shape: {forex_shape}")
            if forex_error:
                print(f"    Error: {forex_error}")
            
            print(f"  - ETF data loaded: {'✓' if etf_data_loaded else '✗'}")
            if etf_data_loaded and etf_shape:
                print(f"    Shape: {etf_shape}")
            if etf_error:
                print(f"    Error: {etf_error}")
            
        except Exception as e:
            self.results['data_loading'] = {
                'status': 'FAILED',
                'error': str(e)
            }
            print(f"✗ Data loading assessment failed: {e}")
        
        print()
    
    def _assess_overall_status(self):
        """Assess overall system status."""
        print("8. OVERALL SYSTEM ASSESSMENT")
        print("-" * 40)
        
        # Count successful components
        successful_components = 0
        total_components = 6
        
        if self.results['database_connection'] and self.results['database_connection'].get('status') == 'SUCCESS':
            successful_components += 1
        
        if self.results['feature_engineering'].get('status') == 'SUCCESS':
            successful_components += 1
        
        if self.results['feature_pruning'].get('status') == 'SUCCESS':
            successful_components += 1
        
        if self.results['autoencoder'].get('status') == 'SUCCESS':
            successful_components += 1
        
        if self.results['policy_network'].get('status') == 'SUCCESS':
            successful_components += 1
        
        if self.results['reward_function'].get('status') == 'SUCCESS':
            successful_components += 1
        
        # Determine overall status
        if successful_components == total_components:
            overall_status = 'FULLY_OPERATIONAL'
        elif successful_components >= 4:
            overall_status = 'MOSTLY_OPERATIONAL'
        elif successful_components >= 2:
            overall_status = 'PARTIALLY_OPERATIONAL'
        else:
            overall_status = 'CRITICAL_FAILURE'
        
        self.results['overall_status'] = overall_status
        
        print(f"✓ Overall system status: {overall_status}")
        print(f"  - Successful components: {successful_components}/{total_components}")
        print(f"  - Success rate: {successful_components/total_components*100:.1f}%")
        
        # Identify critical issues
        critical_issues = []
        if self.results['database_connection'].get('status') != 'SUCCESS':
            critical_issues.append("Database connection")
        if self.results['autoencoder'].get('status') != 'SUCCESS':
            critical_issues.append("Autoencoder")
        if self.results['policy_network'].get('status') != 'SUCCESS':
            critical_issues.append("Policy network")
        
        if critical_issues:
            print(f"  - Critical issues: {', '.join(critical_issues)}")
        
        print()
    
    def _generate_report(self):
        """Generate a comprehensive report."""
        print("9. DIAGNOSTIC REPORT")
        print("=" * 80)
        
        # Save results to file
        report_file = f"rl_system_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"✓ Diagnostic report saved to: {report_file}")
        
        # Print summary
        print(f"\nSUMMARY:")
        print(f"  Overall Status: {self.results['overall_status']}")
        
        # Print recommendations
        print(f"\nRECOMMENDATIONS:")
        
        if self.results['overall_status'] == 'CRITICAL_FAILURE':
            print("  🔴 CRITICAL: System needs immediate attention")
            print("     - Fix database connection issues first")
            print("     - Ensure autoencoder models are available")
            print("     - Verify policy network initialization")
        
        elif self.results['overall_status'] == 'PARTIALLY_OPERATIONAL':
            print("  🟡 PARTIAL: System has major issues but some components work")
            print("     - Focus on missing autoencoder or policy network")
            print("     - Complete feature engineering pipeline")
            print("     - Verify data loading for all instruments")
        
        elif self.results['overall_status'] == 'MOSTLY_OPERATIONAL':
            print("  🟢 MOSTLY: System is mostly functional")
            print("     - Minor fixes needed for full operation")
            print("     - Consider retraining autoencoder if needed")
            print("     - Verify all 20 forex instruments have features")
        
        else:  # FULLY_OPERATIONAL
            print("  🟢 FULLY: System is operational")
            print("     - All components working correctly")
            print("     - Ready for training and inference")
            print("     - Consider performance optimization")
        
        print(f"\nNext steps:")
        print(f"  1. Review the detailed report: {report_file}")
        print(f"  2. Address critical issues identified above")
        print(f"  3. Run training pipeline if system is operational")
        print(f"  4. Test inference on live data")

def main():
    """Run the diagnostic."""
    diagnostic = RLSystemDiagnostic()
    diagnostic.run_full_diagnostic()

if __name__ == "__main__":
    main() 