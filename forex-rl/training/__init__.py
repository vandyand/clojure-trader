# training/__init__.py
from .environment import ForexTradingEnvironment

# Import other modules when they exist
try:
    from .trainer import ForexRLTrainer
except ImportError:
    ForexRLTrainer = None

try:
    from .monitor import TrainingMonitor
except ImportError:
    TrainingMonitor = None

__all__ = ['ForexTradingEnvironment']

# Add to __all__ if available
if ForexRLTrainer is not None:
    __all__.append('ForexRLTrainer')
if TrainingMonitor is not None:
    __all__.append('TrainingMonitor') 