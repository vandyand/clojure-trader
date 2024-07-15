#!/bin/bash

# Create a new Python environment called py-bi-env
python3 -m venv py-bi-env

# Activate the environment
source py-bi-env/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Run the server
python server.py
