# training/monitor.py
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from collections import deque
import warnings

logger = logging.getLogger(__name__)

@dataclass
class MonitoringConfig:
    """Configuration for training monitoring"""
    update_interval: float = 1.0  # Seconds between updates
    plot_update_interval: float = 10.0  # Seconds between plot updates
    alert_thresholds: Dict[str, float] = None
    save_plots: bool = True
    plot_dir: str = "monitoring_plots"
    max_history_length: int = 1000
    enable_alerts: bool = True
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                'min_sharpe_ratio': -2.0,
                'max_drawdown': 0.3,
                'min_win_rate': 0.2,
                'max_loss_streak': 10
            }

@dataclass
class AlertEvent:
    """Alert event data structure"""
    timestamp: float
    alert_type: str
    message: str
    severity: str  # 'info', 'warning', 'critical'
    metric_value: float
    threshold: float

class TrainingMonitor:
    """
    Real-time training monitor with visualization and alerting
    
    Features:
    - Real-time metrics tracking
    - Live plotting and visualization
    - Alert system for performance issues
    - Performance analytics and reporting
    - Thread-safe operation
    """
    
    def __init__(self, config: MonitoringConfig = None):
        """
        Initialize training monitor
        
        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitoringConfig()
        
        # Metrics storage
        self.metrics_history = {
            'timestamps': deque(maxlen=self.config.max_history_length),
            'episode_rewards': deque(maxlen=self.config.max_history_length),
            'episode_returns': deque(maxlen=self.config.max_history_length),
            'sharpe_ratios': deque(maxlen=self.config.max_history_length),
            'max_drawdowns': deque(maxlen=self.config.max_history_length),
            'win_rates': deque(maxlen=self.config.max_history_length),
            'policy_losses': deque(maxlen=self.config.max_history_length),
            'value_losses': deque(maxlen=self.config.max_history_length),
            'entropies': deque(maxlen=self.config.max_history_length),
            'episode_lengths': deque(maxlen=self.config.max_history_length)
        }
        
        # Alert system
        self.alerts = []
        self.alert_callbacks = []
        self.loss_streak = 0
        self.last_return = 0.0
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_plot_update = 0
        
        # Setup directories
        self.plot_dir = Path(self.config.plot_dir)
        self.plot_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.start_time = None
        self.total_episodes = 0
        
        logger.info(f"Initialized TrainingMonitor: update_interval={self.config.update_interval}s")
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.is_monitoring:
            logger.warning("Monitor is already running")
            return
        
        self.is_monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Training monitor started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Training monitor stopped")
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """
        Update metrics from training episode
        
        Args:
            metrics: Dictionary containing episode metrics
        """
        timestamp = time.time()
        
        # Store metrics
        self.metrics_history['timestamps'].append(timestamp)
        self.metrics_history['episode_rewards'].append(metrics.get('total_reward', 0.0))
        self.metrics_history['episode_returns'].append(metrics.get('episode_return', 0.0))
        self.metrics_history['sharpe_ratios'].append(metrics.get('sharpe_ratio', 0.0))
        self.metrics_history['max_drawdowns'].append(metrics.get('max_drawdown', 0.0))
        self.metrics_history['win_rates'].append(metrics.get('win_rate', 0.0))
        self.metrics_history['policy_losses'].append(metrics.get('policy_loss', 0.0))
        self.metrics_history['value_losses'].append(metrics.get('value_loss', 0.0))
        self.metrics_history['entropies'].append(metrics.get('entropy', 0.0))
        self.metrics_history['episode_lengths'].append(metrics.get('episode_length', 0))
        
        self.total_episodes += 1
        
        # Check for alerts
        if self.config.enable_alerts:
            self._check_alerts(metrics)
        
        # Update loss streak
        current_return = metrics.get('episode_return', 0.0)
        if current_return < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0
        
        self.last_return = current_return
    
    def _monitoring_loop(self):
        """Main monitoring loop running in separate thread"""
        while self.is_monitoring:
            try:
                # Update plots if needed
                current_time = time.time()
                if (current_time - self.last_plot_update) >= self.config.plot_update_interval:
                    if len(self.metrics_history['timestamps']) > 0:
                        self._update_plots()
                    self.last_plot_update = current_time
                
                # Sleep until next update
                time.sleep(self.config.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1.0)  # Prevent tight error loop
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check for alert conditions"""
        thresholds = self.config.alert_thresholds
        
        # Sharpe ratio alert
        sharpe_ratio = metrics.get('sharpe_ratio', 0.0)
        if sharpe_ratio < thresholds.get('min_sharpe_ratio', -2.0):
            self._trigger_alert(
                'low_sharpe_ratio',
                f"Sharpe ratio below threshold: {sharpe_ratio:.4f}",
                'warning',
                sharpe_ratio,
                thresholds['min_sharpe_ratio']
            )
        
        # Drawdown alert
        max_drawdown = metrics.get('max_drawdown', 0.0)
        if max_drawdown > thresholds.get('max_drawdown', 0.3):
            self._trigger_alert(
                'high_drawdown',
                f"Drawdown exceeds threshold: {max_drawdown:.4f}",
                'critical',
                max_drawdown,
                thresholds['max_drawdown']
            )
        
        # Win rate alert
        win_rate = metrics.get('win_rate', 0.0)
        if win_rate < thresholds.get('min_win_rate', 0.2) and self.total_episodes > 10:
            self._trigger_alert(
                'low_win_rate',
                f"Win rate below threshold: {win_rate:.4f}",
                'warning',
                win_rate,
                thresholds['min_win_rate']
            )
        
        # Loss streak alert
        if self.loss_streak >= thresholds.get('max_loss_streak', 10):
            self._trigger_alert(
                'loss_streak',
                f"Loss streak reached: {self.loss_streak} episodes",
                'critical',
                self.loss_streak,
                thresholds['max_loss_streak']
            )
    
    def _trigger_alert(self, alert_type: str, message: str, severity: str, 
                      metric_value: float, threshold: float):
        """Trigger an alert"""
        alert = AlertEvent(
            timestamp=time.time(),
            alert_type=alert_type,
            message=message,
            severity=severity,
            metric_value=metric_value,
            threshold=threshold
        )
        
        self.alerts.append(alert)
        
        # Log alert
        log_func = logger.critical if severity == 'critical' else logger.warning
        log_func(f"ALERT [{severity.upper()}]: {message}")
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[AlertEvent], None]):
        """Add callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    def _update_plots(self):
        """Update monitoring plots"""
        if len(self.metrics_history['timestamps']) < 2:
            return
        
        try:
            # Suppress matplotlib warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Create subplots
                fig, axes = plt.subplots(3, 3, figsize=(18, 12))
                fig.suptitle(f'Training Monitor - Episode {self.total_episodes}', fontsize=16)
                
                # Convert deques to lists for plotting
                timestamps = list(self.metrics_history['timestamps'])
                episodes = list(range(len(timestamps)))
                
                # Episode rewards
                axes[0, 0].plot(episodes, list(self.metrics_history['episode_rewards']))
                axes[0, 0].set_title('Episode Rewards')
                axes[0, 0].set_xlabel('Episode')
                axes[0, 0].set_ylabel('Reward')
                axes[0, 0].grid(True, alpha=0.3)
                
                # Episode returns
                axes[0, 1].plot(episodes, list(self.metrics_history['episode_returns']))
                axes[0, 1].set_title('Episode Returns')
                axes[0, 1].set_xlabel('Episode')
                axes[0, 1].set_ylabel('Return')
                axes[0, 1].grid(True, alpha=0.3)
                
                # Sharpe ratios
                axes[0, 2].plot(episodes, list(self.metrics_history['sharpe_ratios']))
                axes[0, 2].axhline(y=0, color='r', linestyle='--', alpha=0.5)
                axes[0, 2].set_title('Sharpe Ratios')
                axes[0, 2].set_xlabel('Episode')
                axes[0, 2].set_ylabel('Sharpe Ratio')
                axes[0, 2].grid(True, alpha=0.3)
                
                # Max drawdowns
                axes[1, 0].plot(episodes, list(self.metrics_history['max_drawdowns']))
                axes[1, 0].set_title('Max Drawdowns')
                axes[1, 0].set_xlabel('Episode')
                axes[1, 0].set_ylabel('Drawdown')
                axes[1, 0].grid(True, alpha=0.3)
                
                # Win rates
                axes[1, 1].plot(episodes, list(self.metrics_history['win_rates']))
                axes[1, 1].axhline(y=0.5, color='r', linestyle='--', alpha=0.5)
                axes[1, 1].set_title('Win Rates')
                axes[1, 1].set_xlabel('Episode')
                axes[1, 1].set_ylabel('Win Rate')
                axes[1, 1].grid(True, alpha=0.3)
                
                # Policy losses
                axes[1, 2].plot(episodes, list(self.metrics_history['policy_losses']))
                axes[1, 2].set_title('Policy Loss')
                axes[1, 2].set_xlabel('Episode')
                axes[1, 2].set_ylabel('Loss')
                axes[1, 2].grid(True, alpha=0.3)
                
                # Value losses
                axes[2, 0].plot(episodes, list(self.metrics_history['value_losses']))
                axes[2, 0].set_title('Value Loss')
                axes[2, 0].set_xlabel('Episode')
                axes[2, 0].set_ylabel('Loss')
                axes[2, 0].grid(True, alpha=0.3)
                
                # Entropies
                axes[2, 1].plot(episodes, list(self.metrics_history['entropies']))
                axes[2, 1].set_title('Policy Entropy')
                axes[2, 1].set_xlabel('Episode')
                axes[2, 1].set_ylabel('Entropy')
                axes[2, 1].grid(True, alpha=0.3)
                
                # Episode lengths
                axes[2, 2].plot(episodes, list(self.metrics_history['episode_lengths']))
                axes[2, 2].set_title('Episode Lengths')
                axes[2, 2].set_xlabel('Episode')
                axes[2, 2].set_ylabel('Steps')
                axes[2, 2].grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                # Save plot
                if self.config.save_plots:
                    plot_path = self.plot_dir / f"monitor_ep{self.total_episodes}.png"
                    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
                
                plt.close()
                
        except Exception as e:
            logger.error(f"Error updating plots: {e}")
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current training statistics"""
        if len(self.metrics_history['timestamps']) == 0:
            return {}
        
        # Calculate statistics
        recent_window = min(50, len(self.metrics_history['episode_rewards']))
        
        stats = {
            'total_episodes': self.total_episodes,
            'training_time': time.time() - self.start_time if self.start_time else 0,
            'current_metrics': {
                'reward': list(self.metrics_history['episode_rewards'])[-1] if self.metrics_history['episode_rewards'] else 0,
                'return': list(self.metrics_history['episode_returns'])[-1] if self.metrics_history['episode_returns'] else 0,
                'sharpe_ratio': list(self.metrics_history['sharpe_ratios'])[-1] if self.metrics_history['sharpe_ratios'] else 0,
                'max_drawdown': list(self.metrics_history['max_drawdowns'])[-1] if self.metrics_history['max_drawdowns'] else 0,
                'win_rate': list(self.metrics_history['win_rates'])[-1] if self.metrics_history['win_rates'] else 0
            },
            'average_metrics': {
                'reward': np.mean(list(self.metrics_history['episode_rewards'])[-recent_window:]) if self.metrics_history['episode_rewards'] else 0,
                'return': np.mean(list(self.metrics_history['episode_returns'])[-recent_window:]) if self.metrics_history['episode_returns'] else 0,
                'sharpe_ratio': np.mean(list(self.metrics_history['sharpe_ratios'])[-recent_window:]) if self.metrics_history['sharpe_ratios'] else 0,
                'max_drawdown': np.mean(list(self.metrics_history['max_drawdowns'])[-recent_window:]) if self.metrics_history['max_drawdowns'] else 0,
                'win_rate': np.mean(list(self.metrics_history['win_rates'])[-recent_window:]) if self.metrics_history['win_rates'] else 0
            },
            'best_metrics': {
                'reward': max(self.metrics_history['episode_rewards']) if self.metrics_history['episode_rewards'] else 0,
                'return': max(self.metrics_history['episode_returns']) if self.metrics_history['episode_returns'] else 0,
                'sharpe_ratio': max(self.metrics_history['sharpe_ratios']) if self.metrics_history['sharpe_ratios'] else 0
            },
            'alerts': {
                'total_alerts': len(self.alerts),
                'recent_alerts': len([a for a in self.alerts if time.time() - a.timestamp < 300]),  # Last 5 minutes
                'loss_streak': self.loss_streak
            }
        }
        
        return stats
    
    def export_data(self, filepath: str):
        """Export monitoring data to file"""
        data = {
            'config': asdict(self.config),
            'metrics_history': {k: list(v) for k, v in self.metrics_history.items()},
            'alerts': [asdict(alert) for alert in self.alerts],
            'stats': self.get_current_stats()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Monitoring data exported to {filepath}")
    
    def generate_report(self) -> str:
        """Generate a text report of training progress"""
        stats = self.get_current_stats()
        
        if not stats:
            return "No training data available"
        
        report = []
        report.append("=" * 60)
        report.append("FOREX RL TRAINING MONITOR REPORT")
        report.append("=" * 60)
        report.append(f"Total Episodes: {stats['total_episodes']}")
        report.append(f"Training Time: {stats['training_time']:.1f}s")
        report.append("")
        
        report.append("CURRENT PERFORMANCE:")
        current = stats['current_metrics']
        report.append(f"  Reward: {current['reward']:.4f}")
        report.append(f"  Return: {current['return']:.4f}")
        report.append(f"  Sharpe Ratio: {current['sharpe_ratio']:.4f}")
        report.append(f"  Max Drawdown: {current['max_drawdown']:.4f}")
        report.append(f"  Win Rate: {current['win_rate']:.4f}")
        report.append("")
        
        report.append("AVERAGE PERFORMANCE (Last 50 episodes):")
        average = stats['average_metrics']
        report.append(f"  Reward: {average['reward']:.4f}")
        report.append(f"  Return: {average['return']:.4f}")
        report.append(f"  Sharpe Ratio: {average['sharpe_ratio']:.4f}")
        report.append(f"  Max Drawdown: {average['max_drawdown']:.4f}")
        report.append(f"  Win Rate: {average['win_rate']:.4f}")
        report.append("")
        
        report.append("BEST PERFORMANCE:")
        best = stats['best_metrics']
        report.append(f"  Best Reward: {best['reward']:.4f}")
        report.append(f"  Best Return: {best['return']:.4f}")
        report.append(f"  Best Sharpe: {best['sharpe_ratio']:.4f}")
        report.append("")
        
        report.append("ALERTS:")
        alerts = stats['alerts']
        report.append(f"  Total Alerts: {alerts['total_alerts']}")
        report.append(f"  Recent Alerts: {alerts['recent_alerts']}")
        report.append(f"  Current Loss Streak: {alerts['loss_streak']}")
        
        if self.alerts:
            report.append("")
            report.append("RECENT ALERTS:")
            recent_alerts = sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:5]
            for alert in recent_alerts:
                report.append(f"  [{alert.severity.upper()}] {alert.message}")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def test_monitor():
    """Test the training monitor"""
    logger.info("Testing training monitor...")
    
    # Create monitor
    config = MonitoringConfig(
        update_interval=0.1,
        plot_update_interval=1.0,
        save_plots=True
    )
    monitor = TrainingMonitor(config)
    
    # Add test alert callback
    def alert_callback(alert: AlertEvent):
        print(f"ALERT: {alert.message}")
    
    monitor.add_alert_callback(alert_callback)
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Simulate training episodes
    for episode in range(20):
        # Simulate metrics
        metrics = {
            'total_reward': np.random.normal(10, 5),
            'episode_return': np.random.normal(0.001, 0.01),
            'sharpe_ratio': np.random.normal(0.5, 1.0),
            'max_drawdown': abs(np.random.normal(0.05, 0.02)),
            'win_rate': np.random.uniform(0.3, 0.7),
            'policy_loss': abs(np.random.normal(0.1, 0.05)),
            'value_loss': abs(np.random.normal(0.05, 0.02)),
            'entropy': abs(np.random.normal(0.5, 0.1)),
            'episode_length': np.random.randint(40, 60)
        }
        
        monitor.update_metrics(metrics)
        time.sleep(0.1)
    
    # Wait for final plot update
    time.sleep(2.0)
    
    # Stop monitoring
    monitor.stop_monitoring()
    
    # Generate report
    report = monitor.generate_report()
    print("\n" + report)
    
    # Export data
    monitor.export_data("test_monitor_data.json")
    
    logger.info("✓ Monitor test completed")
    return True


if __name__ == "__main__":
    test_monitor() 