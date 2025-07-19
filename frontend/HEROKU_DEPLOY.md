# Heroku Deployment Guide

This guide provides step-by-step instructions for deploying the OANDA Trading Dashboard to Heroku, including both the web frontend and the background worker for data collection.

## Prerequisites

- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed
- [Git](https://git-scm.com/) installed
- A Heroku account

## Deployment Steps

### 1. Login to Heroku

```bash
heroku login
```

### 2. Create a new Heroku application

```bash
heroku create your-app-name
```

### 3. Set up environment variables

Set all required environment variables for both the frontend and the worker:

```bash
heroku config:set REACT_APP_SUPABASE_URL=your_supabase_url
heroku config:set REACT_APP_SUPABASE_ANON_KEY=your_supabase_anon_key
heroku config:set REACT_APP_OANDA_LIVE_OR_DEMO=DEMO  # or LIVE
heroku config:set REACT_APP_OANDA_DEMO_URL=https://api-fxpractice.oanda.com/v3/
heroku config:set REACT_APP_OANDA_DEMO_KEY=your_oanda_api_key
heroku config:set REACT_APP_OANDA_DEMO_ACCOUNT_ID=your_oanda_account_id

# If using LIVE environment, also set these:
heroku config:set REACT_APP_OANDA_LIVE_URL=https://api-fxtrade.oanda.com/v3/
heroku config:set REACT_APP_OANDA_LIVE_KEY=your_oanda_live_api_key
heroku config:set REACT_APP_OANDA_LIVE_ACCOUNT_ID=your_oanda_live_account_id
```

### 4. Configure the buildpack for Create React App

```bash
heroku buildpacks:set mars/create-react-app
```

### 5. Deploy the application

From the root of your project:

```bash
git subtree push --prefix frontend-dashboard heroku main
```

If you're deploying from a subdirectory, you need to use git subtree.

### 6. Scale your application

Scale the web process to at least 1 dyno:

```bash
heroku ps:scale web=1
```

Scale the worker process to handle background data collection:

```bash
heroku ps:scale worker=1
```

## Verifying the Deployment

### Check the logs

To verify that both the web app and worker are running correctly:

```bash
# Check web logs
heroku logs --tail --dyno web

# Check worker logs
heroku logs --tail --dyno worker
```

The worker should log messages about fetching data from OANDA and saving to Supabase approximately every 5 minutes.

### Open the application

```bash
heroku open
```

## Troubleshooting

### Worker not running

If the worker is not collecting data:

1. Check the worker logs: `heroku logs --tail --dyno worker`
2. Verify environment variables are set correctly: `heroku config`
3. Restart the worker: `heroku ps:restart worker`

### Web application issues

If the dashboard has issues:

1. Check the web logs: `heroku logs --tail --dyno web`
2. Verify React environment variables are being passed correctly
3. Rebuild and redeploy if necessary

## Maintenance

### Updating the application

When you make changes to your code:

```bash
git subtree push --prefix frontend-dashboard heroku main
```

### Managing dynos

You can turn off dynos when not in use to save on Heroku hours:

```bash
# Turn off worker
heroku ps:scale worker=0

# Turn on worker again
heroku ps:scale worker=1
```

## Additional Resources

- [Heroku DevCenter](https://devcenter.heroku.com/)
- [Heroku Node.js Support](https://devcenter.heroku.com/articles/nodejs-support)
- [Heroku Procfile](https://devcenter.heroku.com/articles/procfile)
- [Heroku Scheduler](https://devcenter.heroku.com/articles/scheduler) (Alternative to custom worker)
