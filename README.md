# Job Alert Agent 🤖

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-3.x-green)
![Telegram](https://img.shields.io/badge/Alerts-Telegram-26A5E4?logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/Dedup-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Autonomous agent that monitors 27 tech company career sites 24/7 and fires Telegram alerts the moment a CS student or intern role goes live — before it reaches LinkedIn.**

<!-- demo GIF placeholder -->

---

## The Problem

Student and intern roles at top tech companies fill fast. By the time a listing appears on LinkedIn, it has already been live on the company's own career site for hours — and the first wave of applicants has already applied. Checking 27 portals manually throughout the day is not realistic.

## The Solution

Job Alert Agent runs continuously on a cloud server, querying company career sites **directly** through their native APIs — Workday, SmartRecruiters, Greenhouse, and custom endpoints. A four-stage filter pipeline removes irrelevant noise. Alerts land in Telegram within minutes of a job going live, days before aggregators index it.

---

## Architecture

```
  Career Sites                Filter Engine              Delivery
  ────────────                ─────────────              ────────
  Workday API    ──┐
  SmartRecruiters──┤   title filter       ┌── SQLite ──▶ Telegram alert
  Greenhouse API ──┼──▶ blocklist    ──▶  │   dedup      (per job)
  Amazon Jobs    ──┤   CS description     └── new? ───▶ Daily digest
  LinkedIn/Indeed──┘   location filter         │          08:00
                                               ▼
                                           jobs.db
```

---

## How It Works

- **Multi-source scraping** — direct Workday/SmartRecruiters/Greenhouse API calls plus LinkedIn and Indeed via JobSpy
- **Title filter** — job must contain `intern`, `internship`, or `student` (hard gate, no exceptions)
- **Blocklist** — drops non-CS roles: finance, HR, legal, marketing, sales, supply chain, biology, and 10+ more
- **CS description check** — if a description is available (>100 chars), it must mention computer science, software engineering, or equivalent Hebrew terms (`תואר`, `מדעי המחשב`)
- **Location filter** — Israeli cities only; international roles are silently dropped
- **Deduplication** — job ID is `MD5(title + company)`, so the same role appearing on LinkedIn and Workday is sent exactly once
- **Daily digest** — every morning at 08:00, a summary of the last 24 hours is sent regardless of individual alerts

---

## Companies Covered

NVIDIA · Intel · Amazon · Google · Microsoft · Apple · Meta · Mobileye · Qualcomm · Palo Alto Networks · Check Point · Wix · Monday.com · CyberArk · Cisco · Broadcom · Arm · Samsung · Synopsys · Cadence · Amdocs · Akamai · Varonis · Fiverr · Gett · Nice · Tower Semiconductor — plus IAI, Rafael, and Elbit via daily defense scan.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| LinkedIn / Indeed | [JobSpy](https://github.com/Bunsly/JobSpy) |
| Scheduling | APScheduler 3.x (cron triggers) |
| Deduplication | SQLite 3 |
| Notifications | python-telegram-bot 20.x |
| Direct API calls | Requests |
| Config | YAML |
| Deployment | Oracle Cloud / DigitalOcean + systemd |

---

## Project Structure

```
job-alert-agent/
├── src/
│   ├── main.py                    # Scheduler, orchestration, DRY_RUN flag
│   ├── scraper.py                 # LinkedIn/Indeed via JobSpy — 3 tiers
│   ├── workday_scraper.py         # Workday direct API (NVIDIA, Intel)
│   ├── smartrecruiters_scraper.py # SmartRecruiters API (22 companies)
│   ├── greenhouse_scraper.py      # Greenhouse API (Nice)
│   ├── amazon_scraper.py          # Amazon Jobs direct API
│   ├── google_scraper.py          # Google Careers API
│   ├── filters.py                 # Shared CS description filter
│   ├── notifier.py                # Telegram alerts + daily digest
│   └── db.py                      # SQLite: init, dedup, recent jobs
├── config/
│   ├── config.yaml                # All targeting config — companies, locations, schedule
│   └── .env.example               # Environment variable template
├── scripts/
│   ├── setup.sh                   # One-command server setup
│   ├── start.sh                   # Activate venv + run
│   └── update.sh                  # git pull + graceful restart
├── deploy/
│   └── render.yaml                # Render.com worker service config
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/omerbacher/Job-Alert-Agent.git
cd Job-Alert-Agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp config/.env.example .env
# Fill in TELEGRAM_TOKEN and TELEGRAM_CHAT_ID

# 3. Run
python src/main.py
```

Get your credentials: bot token from [@BotFather](https://t.me/BotFather) · chat ID from [@userinfobot](https://t.me/userinfobot)

**Deploy to a VPS:**
```bash
bash <(curl -s https://raw.githubusercontent.com/omerbacher/Job-Alert-Agent/main/scripts/setup.sh)
# then: fill .env, run: bash scripts/start.sh
```

---

## License

MIT
