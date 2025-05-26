#!/usr/bin/env python3
"""
Test script for neural networks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from models.network import test_network_forward_pass

if __name__ == "__main__":
    test_network_forward_pass() 