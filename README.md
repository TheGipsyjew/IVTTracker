# IVT Community Bot

This bot logs into `https://app.interactivtrading.com/` and scrapes the latest community posts from the feed.

## Prerequisites

- Python 3.10+
- Chrome browser (Botasaurus uses the installed Chrome/Chromium)

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure credentials:
   Ensure your `.env` file has the correct login details:
   ```env
   IVT_USERNAME="YourUsername"
   IVT_PASSWORD="YourPassword"
   ```

## Usage

Run the bot script:
```bash
python src/bot.py
```

The bot will:
1. Launch a browser (headless mode by default).
2. Log in using the credentials.
3. Scrape the latest posts.
4. Save the posts to `posts.json`.

## Configuration

- **Visual Mode**: To see the browser running, change `headless=True` to `headless=False` in `src/bot.py`.
- **Profile**: The bot uses a persistent profile `ivt_tracker_main` to maintain cookies/session.
