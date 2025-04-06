#!/usr/bin/env bash
# deploy-frontend-heroku.sh - Deploy the React frontend to Heroku

set -e

echo "Deploying Clojure Trader Frontend to Heroku..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Error: Heroku CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in
if ! heroku auth:whoami &> /dev/null; then
    echo "You need to be logged in to Heroku."
    heroku login
fi

# Ask for the app name
read -p "Enter your Heroku app name for the frontend (e.g., clojure-trader-frontend): " APP_NAME

# Check if the app exists
if ! heroku apps:info --app "$APP_NAME" &> /dev/null; then
    echo "Error: App $APP_NAME does not exist."
    echo "Would you like to create it? (y/n)"
    read -r CREATE_APP
    if [[ $CREATE_APP =~ ^[Yy]$ ]]; then
        heroku apps:create "$APP_NAME" --buildpack https://github.com/mars/create-react-app-buildpack.git
        echo "App created successfully!"
    else
        exit 1
    fi
fi

# Build the frontend
echo "Building the frontend application..."
npm run build

# Set API URL environment variable
read -p "Enter the API URL (e.g., https://clojure-trader-api-18279899daf7.herokuapp.com): " API_URL
heroku config:set REACT_APP_CLOJURE_API_URL="$API_URL" --app "$APP_NAME"
heroku config:set REACT_APP_DEFAULT_API_SOURCE=clojure --app "$APP_NAME"

# Configure the git remote for the frontend app
if ! git remote | grep -q "heroku-frontend"; then
    echo "Adding heroku-frontend remote..."
    git remote add heroku-frontend "https://git.heroku.com/$APP_NAME.git"
fi

# Push the code to Heroku
echo "Pushing code to Heroku..."
git push heroku-frontend `git subtree split --prefix frontend master`:master --force

echo "Deployment complete!"
echo "Your frontend application is now available at: https://$APP_NAME.herokuapp.com"

# Setup CORS origin for the backend if needed
read -p "Do you want to set CORS configuration on the backend to allow this frontend? (y/n): " SETUP_CORS
if [[ $SETUP_CORS =~ ^[Yy]$ ]]; then
    read -p "Enter your backend app name (e.g., clojure-trader-api): " BACKEND_APP
    heroku config:set CORS_ORIGIN="https://$APP_NAME.herokuapp.com" --app "$BACKEND_APP"
    echo "CORS origin set to https://$APP_NAME.herokuapp.com on $BACKEND_APP"
fi

echo "Frontend deployment process completed!" 