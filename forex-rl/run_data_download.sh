#!/bin/bash

# Run the forex data download script with full settings
python3 scripts/data_download.py --full

# Check if the script executed successfully
if [ $? -eq 0 ]; then
    echo "✅ Data download completed successfully"
else
    echo "❌ Data download failed"
    exit 1
fi
