#!/usr/bin/env bash
# deploy-all.sh - Deploy both the backend and frontend to Heroku

set -e

echo "===================================="
echo "🚀 Deploying Clojure Trader to Heroku"
echo "===================================="

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Error: Heroku CLI is not installed. Please install it first."
    exit 1
fi

# Step 1: Deploy the backend
echo "Step 1: Deploying the backend..."
./deploy-to-heroku.sh

# Step 2: Deploy the frontend
echo "Step 2: Deploying the frontend..."
./deploy-frontend-heroku.sh

echo "===================================="
echo "🎉 Deployment complete!"
echo "===================================="
echo "Your application is now available at:"
echo "- Backend: https://clojure-trader-api-18279899daf7.herokuapp.com"
echo "- Frontend: https://clojure-trader-dashboard-c45d41aa0c18.herokuapp.com"
echo ""
echo "Next steps:"
echo "1. Register an account at the frontend"
echo "2. Configure your trading accounts"
echo "3. Run backtests and analyze results"
echo "====================================" 