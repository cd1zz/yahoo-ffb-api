# Getting Started with Yahoo Fantasy Football API SDK

This step-by-step guide will help you set up and use the Yahoo Fantasy Football API SDK for the first time.

## Prerequisites

- Python 3.9 or higher
- A Yahoo account with access to Fantasy Football leagues

## Step 1: Create a Yahoo Developer App

1. Go to [Yahoo Developer Apps](https://developer.yahoo.com/apps/create/)
2. Click "Create an App"
3. Fill out the form:
   - **Application Name**: Your app name (e.g., "My Fantasy Tool")
   - **Application Type**: Web Application
   - **Description**: Brief description of your app
   - **Home Page URL**: Can be your GitHub repo or any URL
   - **Redirect URI(s)**: `http://127.0.0.1:8765/callback`
   - **API Permissions**: Check "Fantasy Sports" and select "Read"
4. Click "Create App"
5. Save your **Client ID** and **Client Secret**

> **Note**: If Yahoo forces HTTPS, use `https://127.0.0.1:8765/callback` instead. The SDK handles both HTTP and HTTPS automatically.

## Step 2: Install the SDK

```bash
pip install yahoo-ffb-api
```

## Step 3: Configure Your Credentials

1. Copy the example environment file:
```bash
cp .env.example .env  # Linux/Mac
# or
Copy-Item .env.example .env  # Windows PowerShell
```

2. Edit `.env` with your Yahoo app credentials:
```env
YAHOO_CLIENT_ID=your_actual_client_id
YAHOO_CLIENT_SECRET=your_actual_client_secret
YAHOO_REDIRECT_URI=http://127.0.0.1:8765/callback
YAHOO_SCOPE=fspt-r
```

## Step 4: Authenticate with Yahoo

```bash
yfa auth
```

This will:
1. Open your browser to Yahoo's login page
2. Ask you to authorize your app  
3. Save the authentication token locally

## Step 5: Test Your Setup

```bash
# Verify authentication works
yfa verify

# List your fantasy leagues
yfa leagues

# Get details about a specific league
yfa league-info <your_league_key>
```

## Your First Commands

### Find Your League Keys
League IDs change every season, so always start by finding current league keys:

```bash
# Current season
yfa leagues

# Previous seasons
yfa leagues --year 2024
yfa leagues --year 2023
```

### Basic League Operations
```bash
# Get league information
yfa league-info 461.l.123456

# View current standings  
yfa standings 461.l.123456

# See this week's matchups
yfa weekly-scoreboard 461.l.123456 5

# Check draft results
yfa draft-picks 461.l.123456
```

### Watch a Live Draft
```bash
# Monitor draft picks in real-time
yfa draft-picks 461.l.123456 --watch

# Show recent picks and watch for new ones
yfa draft-picks 461.l.123456 --recent 10 --watch
```

## Next Steps

- Read the full [API documentation](README.md) for all available commands
- See [examples](README.md#examples) for advanced usage patterns
- Join [discussions](https://github.com/CraigFreyman/yahoo-ffb-api/discussions) with other users

## Common Issues

### "No leagues found"
- Make sure you're authenticated: `yfa verify`
- Try different years: `yfa leagues --year 2024`
- Verify you have Fantasy Football leagues in that Yahoo account

### Authentication Problems
- Double-check your Client ID and Secret in `.env`
- Ensure redirect URI matches exactly between Yahoo app and `.env`
- Re-run `yfa auth` if tokens seem corrupted

### HTTPS Certificate Warnings
- If using HTTPS callback, your browser may show security warnings
- Click "Advanced" → "Proceed to localhost" - this is safe for local development
- The authentication will complete successfully

Need more help? Check the [full documentation](README.md) or [create an issue](https://github.com/CraigFreyman/yahoo-ffb-api/issues).
