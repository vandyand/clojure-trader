#!/usr/bin/env python3
"""
Test script for RL trainer
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from training.trainer import test_trainer

if __name__ == "__main__":
    test_trainer() 