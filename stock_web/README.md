# Stock Assistant Web

Stock Assistant Web is a Flask-based stock analysis and paper-trading application.  
It was migrated from a desktop GUI project into a browser-first workflow with multiple pages and integrated notification channels.

## Language Versions

- English (default): [README.md](README.md)
- 中文: [README.zh-CN.md](README.zh-CN.md)
- 日本語: [README.ja.md](README.ja.md)

## Project Overview

This project provides:

- Market overview dashboard (A-share, HK, US)
- Watchlist management
- News and sentiment feed
- Strategy screener with pagination
- Paper trading (buy/sell/positions)
- Notification center and settings panel

## Key Features

- Real-time quote fetch with source fallback
- Multi-market gainers/losers recommendation blocks
- News aggregation with timeline display
- One-click watchlist actions from multiple pages
- Built-in paper trading and PnL tracking
- Configurable notifications:
  - PushPlus
  - Twilio WhatsApp
  - Telegram

## Tech Stack

- Python
- Flask
- SQLite (local data persistence)
- Vanilla JS + jQuery
- HTML templates + CSS

## Quick Start

### Option A: Beginner-friendly launcher (recommended)

On Windows:

```bat
run.bat
```

The launcher will:

- Detect local Python installations
- Let you choose one by index if multiple are found
- Install dependencies automatically
- Start the app
- Show Python download link when Python is missing

On Linux/macOS:

```bash
bash run.sh
```

### Option B: Manual setup

1) Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2) Run the app:

```bash
python app.py
```

3) Open in browser:

`http://127.0.0.1:5000`

## Configuration

Go to the **Settings** page to configure:

- Tushare token
- PushPlus token
- Twilio credentials and phone numbers
- Telegram bot token and chat ID

## Project Structure

- `app.py`: Flask entrypoint
- `backend/`: routes and service layer
- `core/`: business logic and integrations
- `templates/`: HTML pages
- `static/`: JavaScript and CSS assets
- `data/`: config and SQLite database
- `run.bat`, `run_windows.ps1`, `run.sh`: startup scripts

## Main Dependencies

See `requirements.txt`:

- flask
- tushare
- requests
- pandas
- numpy
- mplfinance
- cryptography
- apscheduler
- twilio
- python-telegram-bot
- tickflow
