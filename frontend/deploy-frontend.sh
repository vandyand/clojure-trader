#!/usr/bin/env bash
# deploy-frontend.sh - Deploy the React frontend to GitHub Pages or similar static hosting

set -e

echo "Deploying Frontend for Clojure Trader..."

# Build the frontend
echo "Building the frontend application..."
npm run build

# Ask which hosting service to use
echo "Select a hosting service for deployment:"
echo "1) GitHub Pages"
echo "2) Netlify"
echo "3) Vercel"
echo "4) Manual (just build)"
read -p "Enter your choice (1-4): " HOSTING_CHOICE

case $HOSTING_CHOICE in
    1)
        # Deploy to GitHub Pages
        echo "Deploying to GitHub Pages..."
        if ! command -v gh &> /dev/null; then
            echo "GitHub CLI is not installed. Please install it to deploy to GitHub Pages."
            echo "Visit: https://cli.github.com/manual/installation"
            exit 1
        fi

        # Ensure we have a gh-pages branch
        if ! git rev-parse --verify gh-pages &> /dev/null; then
            echo "Creating gh-pages branch..."
            git checkout --orphan gh-pages
            git rm -rf .
            echo "# Clojure Trader Frontend" > README.md
            git add README.md
            git commit -m "Initialize gh-pages branch"
            git push origin gh-pages
            git checkout master
        fi

        # Add CNAME if needed
        read -p "Do you want to use a custom domain? (y/n): " USE_CUSTOM_DOMAIN
        if [[ $USE_CUSTOM_DOMAIN =~ ^[Yy]$ ]]; then
            read -p "Enter your custom domain (e.g., trading.example.com): " CUSTOM_DOMAIN
            echo "$CUSTOM_DOMAIN" > build/CNAME
        fi

        # Deploy using gh-pages or manually
        if command -v npx &> /dev/null; then
            npx gh-pages -d build
        else
            echo "Manual deploy to gh-pages branch..."
            cp -r build /tmp/clojure-trader-build
            git checkout gh-pages
            rm -rf *
            cp -r /tmp/clojure-trader-build/* .
            git add .
            git commit -m "Update frontend build"
            git push origin gh-pages
            git checkout master
            rm -rf /tmp/clojure-trader-build
        fi
        echo "Deployed to GitHub Pages!"
        ;;
    2)
        # Deploy to Netlify
        echo "Deploying to Netlify..."
        if ! command -v netlify &> /dev/null; then
            echo "Netlify CLI is not installed. Installing it now..."
            npm install -g netlify-cli
        fi
        netlify deploy --prod --dir=build
        ;;
    3)
        # Deploy to Vercel
        echo "Deploying to Vercel..."
        if ! command -v vercel &> /dev/null; then
            echo "Vercel CLI is not installed. Installing it now..."
            npm install -g vercel
        fi
        vercel --prod
        ;;
    4)
        # Manual deployment (just build)
        echo "Frontend built successfully but not deployed."
        echo "The build files are available in the 'build' directory."
        echo "You can manually upload these files to your preferred hosting service."
        ;;
    *)
        echo "Invalid choice. Frontend built but not deployed."
        ;;
esac

echo "Frontend deployment process completed!" 