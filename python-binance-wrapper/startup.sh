#!/bin/bash

# Check if we're already in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Creating new environment..."
    
    # Remove existing environment if it exists
    rm -rf py-bi-env 2>/dev/null
    
    # Try using the system Python instead of pyenv
    /usr/bin/python3 -m pip install --user flask ccxt pandas requests python-dotenv
    
    # Run the server with system Python
    /usr/bin/python3 server.py
else
    echo "Using existing environment: $VIRTUAL_ENV"
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Run the server
    python server.py
fi
