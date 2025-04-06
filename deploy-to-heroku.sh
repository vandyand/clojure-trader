#!/usr/bin/env bash
# deploy-to-heroku.sh - Deploy Clojure Trader to Heroku

set -e

echo "Deploying Clojure Trader to Heroku..."

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
read -p "Enter your Heroku app name (e.g., clojure-trader-api): " APP_NAME

# Check if the app exists
if ! heroku apps:info --app "$APP_NAME" &> /dev/null; then
    echo "Error: App $APP_NAME does not exist."
    echo "Would you like to create it? (y/n)"
    read -r CREATE_APP
    if [[ $CREATE_APP =~ ^[Yy]$ ]]; then
        heroku apps:create "$APP_NAME"
        echo "App created successfully!"
    else
        exit 1
    fi
fi

# Check if PostgreSQL addon is installed
if ! heroku addons:info --app "$APP_NAME" | grep -q "heroku-postgresql"; then
    echo "PostgreSQL addon is not installed. Would you like to run the PostgreSQL setup script? (y/n)"
    read -r SETUP_PG
    if [[ $SETUP_PG =~ ^[Yy]$ ]]; then
        ./heroku-postgres-setup.sh
    else
        echo "Warning: PostgreSQL is required for the app to function correctly."
    fi
fi

# Push to Heroku
echo "Pushing code to Heroku..."
if git remote | grep -q "heroku"; then
    echo "Heroku remote already exists, using it."
else
    echo "Adding Heroku remote..."
    git remote add heroku "https://git.heroku.com/$APP_NAME.git"
fi

git push heroku master

echo "Deployment complete!"
echo "Your application is now available at: https://$APP_NAME.herokuapp.com" 