#!/bin/bash

# Create a new Python environment called py-rh-env
python3 -m venv py-rh-env

# Activate the environment
source py-rh-env/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Run the server
python server.py
