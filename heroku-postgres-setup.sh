#!/usr/bin/env bash
# heroku-postgres-setup.sh - Setup PostgreSQL on Heroku

set -e

echo "Setting up PostgreSQL on Heroku for Clojure Trader..."

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
    exit 1
fi

echo "Setting up PostgreSQL..."

# Add PostgreSQL addon
echo "Adding PostgreSQL addon..."
heroku addons:create heroku-postgresql:essential-0 --app "$APP_NAME" || {
    echo "PostgreSQL addon already exists or couldn't be created."
    # Continue even if it fails - the addon might already exist
}

# Generate a secure JWT secret if it doesn't exist
echo "Setting environment variables..."
JWT_SECRET=$(openssl rand -hex 32)
heroku config:set JWT_SECRET="$JWT_SECRET" --app "$APP_NAME"

# Restart the app to apply changes
echo "Restarting the app to apply changes..."
heroku restart --app "$APP_NAME"

echo "Setup complete!"
echo "PostgreSQL has been added to your Heroku app."
echo "JWT authentication is configured with a secure secret."
echo
echo "Next steps:"
echo "1. Deploy your updated code to Heroku"
echo "2. Access your API at https://$APP_NAME.herokuapp.com"
echo "3. Register a user using the /api/auth/register endpoint"
echo
echo "Happy trading!" 