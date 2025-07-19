#!/bin/bash

# Script to set up Heroku with TimescaleDB and JWT authentication

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Heroku with TimescaleDB and JWT authentication...${NC}"

# Check if Heroku CLI is installed
if ! command -v heroku >/dev/null 2>&1; then
  echo -e "${RED}Heroku CLI is not installed. Please install it first.${NC}"
  echo "Visit https://devcenter.heroku.com/articles/heroku-cli for installation instructions."
  exit 1
fi

# Check if user is logged in to Heroku
if ! heroku auth:whoami >/dev/null 2>&1; then
  echo -e "${RED}You are not logged in to Heroku. Please login first.${NC}"
  heroku login
fi

# Get the app name
read -p "Enter your Heroku app name (e.g., clojure-trader-api): " APP_NAME

if [ -z "$APP_NAME" ]; then
  echo -e "${RED}App name cannot be empty.${NC}"
  exit 1
fi

# Check if the app exists
if ! heroku apps:info --app "$APP_NAME" >/dev/null 2>&1; then
  echo -e "${RED}App $APP_NAME does not exist. Please create it first.${NC}"
  exit 1
fi

echo -e "${GREEN}Setting up TimescaleDB...${NC}"

# Add TimescaleDB addon
if heroku addons:info --app "$APP_NAME" timescaledb >/dev/null 2>&1; then
  echo -e "${BLUE}TimescaleDB already exists for this app.${NC}"
else
  echo -e "${BLUE}Adding TimescaleDB addon...${NC}"
  heroku addons:create timescaledb:starter --app "$APP_NAME"
fi

# Generate a secure JWT secret
JWT_SECRET=$(openssl rand -hex 32)

# Set environment variables
echo -e "${BLUE}Setting environment variables...${NC}"
heroku config:set JWT_SECRET="$JWT_SECRET" --app "$APP_NAME"

# Restart the app to apply changes
echo -e "${BLUE}Restarting the app to apply changes...${NC}"
heroku restart --app "$APP_NAME"

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}TimescaleDB has been added to your app.${NC}"
echo -e "${BLUE}JWT authentication is configured with a secure secret.${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Deploy your updated code to Heroku"
echo -e "2. Access your API at https://$APP_NAME.herokuapp.com"
echo -e "3. Register a user using the /api/auth/register endpoint"
echo -e "${GREEN}Happy trading!${NC}" 