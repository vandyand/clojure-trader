#!/usr/bin/env python3
"""
Test script for reward function
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from models.reward import test_reward_function

if __name__ == "__main__":
    test_reward_function() 