#!/usr/bin/env bash
# update-github-urls.sh - Update GitHub repository with deployment URLs

set -e

# Default values - change these to match your repository
OWNER=$(git config --get remote.origin.url | sed -n 's/.*github.com[:/]\(.*\)\/\(.*\)\.git.*/\1/p')
REPO=$(git config --get remote.origin.url | sed -n 's/.*github.com[:/]\(.*\)\/\(.*\)\.git.*/\2/p')
FRONTEND_URL="https://clojure-trader-dashboard-c45d41aa0c18.herokuapp.com"
BACKEND_URL="https://clojure-trader-api-18279899daf7.herokuapp.com"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI is not installed. Please install it first."
    echo "Visit: https://cli.github.com/manual/installation"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "You need to be logged in to GitHub CLI."
    gh auth login
fi

echo "===================================="
echo "🔗 Updating GitHub Repository URLs"
echo "===================================="
echo "Owner: $OWNER"
echo "Repository: $REPO"
echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL: $BACKEND_URL"

# Update repository homepage
echo "Setting repository homepage to frontend URL..."
gh api -X PATCH "repos/$OWNER/$REPO" -f homepage="$FRONTEND_URL"
echo "✅ Repository homepage updated"

# Create README badge section if it doesn't exist
if ! grep -q "## Deployment Status" README.md; then
    echo "Adding deployment status section to README..."
    cat >> README.md << EOL

## Deployment Status

[![Frontend](https://img.shields.io/badge/Frontend-Deployed-brightgreen)](${FRONTEND_URL})
[![Backend](https://img.shields.io/badge/Backend-Deployed-brightgreen)](${BACKEND_URL})

EOL
    echo "✅ Added deployment status badges to README"
fi

# Add GitHub repository topics for better discoverability
echo "Adding repository topics..."
gh api -X PUT "repos/$OWNER/$REPO/topics" -f names[]="clojure" -f names[]="trading" -f names[]="react" -f names[]="heroku-deployed"
echo "✅ Repository topics updated"

# Create GitHub environments if they don't exist
echo "Creating GitHub environments..."

# Production environment for frontend
gh api -X PUT "repos/$OWNER/$REPO/environments/frontend-production" \
  -f wait_timer=0 \
  -f deployment_branch_policy=null
echo "✅ Frontend production environment created"

# Production environment for backend
gh api -X PUT "repos/$OWNER/$REPO/environments/backend-production" \
  -f wait_timer=0 \
  -f deployment_branch_policy=null
echo "✅ Backend production environment created"

echo "===================================="
echo "✨ GitHub Repository Updated"
echo "===================================="
echo "Your repository now links to your deployed applications."
echo "Visit your repository at: https://github.com/$OWNER/$REPO"
echo "====================================" 