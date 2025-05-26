#!/usr/bin/env python3
"""
Test script for OANDA API integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from data.oanda_client import test_oanda_client

if __name__ == "__main__":
    test_oanda_client() 