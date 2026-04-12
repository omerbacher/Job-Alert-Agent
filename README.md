# Job Alert Agent

A background agent that scrapes job postings every 10 minutes (8am–10pm), scores each job against your CV using Claude, and sends Telegram alerts for strong matches.

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | How to get it |
|---|---|
| `TELEGRAM_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Message [@userinfobot](https://t.me/userinfobot) to get your chat ID |
| `ANTHROPIC_API_KEY` | Get from [console.anthropic.com](https://console.anthropic.com) |

### 4. Add your CV (optional but recommended)

Create a `cv.txt` file in the project root with the plain-text content of your CV.
Without it, every job defaults to a score of 75.

```bash
# Paste your CV text into this file
notepad cv.txt
```

### 5. Adjust config.yaml (optional)

Edit `config.yaml` to change:
- `keywords` — job title keywords to search and filter by
- `companies` — companies to prioritise
- `locations` — search locations
- `min_score` — minimum score (0–100) to trigger an alert
- `hours_active_start` / `hours_active_end` — active window (default 8am–10pm)

### 6. Run the agent

```bash
python main.py
```

The agent will scan immediately on startup, then repeat every 10 minutes during active hours.

## Project structure

```
job-alert-agent/
├── main.py          # Entry point & scheduler
├── scraper.py       # Job scraping (LinkedIn + Indeed via jobspy)
├── scorer.py        # CV-to-job scoring via Claude API
├── notifier.py      # Telegram alert sender
├── db.py            # SQLite deduplication store
├── config.yaml      # Search settings
├── cv.txt           # Your CV (you create this)
├── .env             # Secrets (you create this from .env.example)
├── .env.example     # Template for secrets
└── requirements.txt
```

## How it works

1. **Scraper** queries LinkedIn and Indeed for each keyword × location combination.
2. **Filter** keeps only jobs whose title contains a keyword and whose company is on the target list (or the keyword already qualifies the title).
3. **Deduplication** skips jobs already stored in `jobs.db`.
4. **Scorer** sends the job + your CV to Claude and gets back a 0–100 match score.
5. **Notifier** sends a Telegram message for any job scoring ≥ `min_score`.
6. **DB** records every processed job so it is never alerted twice.
