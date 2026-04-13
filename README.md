# Job Alert Agent 🤖

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-3.x-green)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

> Autonomous 24/7 job monitoring agent — scrapes 27 tech company career sites directly and delivers instant Telegram alerts for CS student roles.

---

## The Problem

Student and intern roles at top tech companies disappear within hours of posting — sometimes minutes. By the time a listing surfaces on LinkedIn or an aggregator, hundreds of applicants have already applied. Manually checking 27 different career portals throughout the day is not a realistic strategy.

## The Solution

Job Alert Agent runs 24/7 on a cloud server, querying company career sites **directly** through their native APIs — Workday, SmartRecruiters, Greenhouse, and custom endpoints — before listings ever propagate to LinkedIn. A multi-stage filter engine ensures only relevant CS student and intern roles reach you. Alerts arrive on Telegram within minutes of a job going live.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Scraper Layer                       │
│  LinkedIn/Indeed · Workday · SmartRecruiters (22 cos)   │
│  Greenhouse · Amazon Jobs API · Google Careers          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Filter Engine                        │
│  1. Title      → must contain intern / student          │
│  2. Blocklist  → drops finance, HR, legal, marketing…   │
│  3. Description→ must reference CS / software eng.      │
│  4. Location   → Israel cities only                     │
│  5. Company    → must be on the configured target list  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               Deduplication  (SQLite)                   │
│   ID = MD5(title.lower() | company.lower())             │
│   Same job appearing on multiple platforms → sent once  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Telegram Delivery                      │
│   Instant per-job alert + daily 08:00 digest            │
└─────────────────────────────────────────────────────────┘
```

---

## Data Sources

| Company | Platform | Tier |
|---------|----------|------|
| NVIDIA | Workday (direct API) | Priority |
| Intel | Workday (direct API) | Priority |
| Amazon | Amazon Jobs API | Priority |
| Google | SmartRecruiters | Priority |
| Microsoft | SmartRecruiters | Priority |
| Apple | SmartRecruiters | Priority |
| Meta | LinkedIn / Indeed | Priority |
| Mobileye | SmartRecruiters | Priority |
| Qualcomm | SmartRecruiters | Priority |
| Palo Alto Networks | SmartRecruiters | Priority |
| Check Point | SmartRecruiters | Priority |
| Wix | SmartRecruiters | Regular |
| Monday.com | SmartRecruiters | Regular |
| Amdocs | SmartRecruiters | Regular |
| Tower Semiconductor | SmartRecruiters | Regular |
| Cadence | SmartRecruiters | Regular |
| Synopsys | SmartRecruiters | Regular |
| Cisco | SmartRecruiters | Regular |
| Samsung | SmartRecruiters | Regular |
| Broadcom | SmartRecruiters | Regular |
| Arm | SmartRecruiters | Regular |
| Akamai | SmartRecruiters | Regular |
| CyberArk | SmartRecruiters | Regular |
| Varonis | SmartRecruiters | Regular |
| Fiverr | SmartRecruiters | Regular |
| Gett | SmartRecruiters | Regular |
| Nice | Greenhouse API | Regular |
| IAI / Rafael / Elbit | LinkedIn / Indeed | Defense (daily) |

---

## Filter Pipeline

Every scraped job passes through five sequential filters before an alert is sent:

**1. Title filter**
Title must contain `intern`, `internship`, or `student`. Hard requirement — no exceptions.

**2. Blocklist**
Drops titles containing non-CS terms: `economics`, `marketing`, `finance`, `accounting`, `HR`, `legal`, `sales`, `supply chain`, `logistics`, `graphic`, `recruiter`, `biology`, `chemistry`, `medical`, `law`, `MBA`, and others.

**3. CS description check**
When a job description is available and longer than 100 characters, it must mention at least one of: `computer science`, `computer engineering`, `software engineering`, `CS degree`, `B.Sc`, `תואר`, `מדעי המחשב`. Jobs with no description pass through (benefit of the doubt).

**4. Location filter**
Job location must match one of the configured Israeli cities. Prevents international roles from leaking through.

**5. Company filter**
For LinkedIn/Indeed results, the company name must exactly match one on the target list (case-insensitive). Direct API scrapers are already scoped per-company.

---

## Scanning Schedule

| Scanner | Frequency | Window |
|---------|-----------|--------|
| Priority companies (LinkedIn/Indeed) | Every 10 min | 08:00–22:00 |
| Workday — NVIDIA, Intel | Every 10 min | 08:00–22:00 |
| Amazon Jobs API | Every 10 min | 08:00–22:00 |
| SmartRecruiters — 22 companies | Every 30 min | 08:00–22:00 |
| Greenhouse — Nice | Every 30 min | 08:00–22:00 |
| Regular companies (LinkedIn/Indeed) | Every 30 min | 08:00–22:00 |
| Defense companies (LinkedIn/Indeed) | Once daily | 09:00 |
| Daily digest | Once daily | 08:00 |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| LinkedIn / Indeed scraping | [JobSpy](https://github.com/Bunsly/JobSpy) |
| Scheduling | APScheduler 3.x |
| Deduplication store | SQLite 3 |
| Telegram notifications | python-telegram-bot 20.x |
| HTTP / direct API requests | Requests |
| Config management | YAML |
| Deployment | Oracle Cloud / DigitalOcean + systemd |

---

## Project Structure

```
job-alert-agent/
├── main.py                    # Scheduler, orchestration, DRY_RUN flag
├── scraper.py                 # LinkedIn/Indeed scraper via JobSpy (3 tiers)
├── workday_scraper.py         # Workday direct API — NVIDIA, Intel
├── smartrecruiters_scraper.py # SmartRecruiters API — 22 companies
├── greenhouse_scraper.py      # Greenhouse API — Nice
├── amazon_scraper.py          # Amazon Jobs direct API
├── google_scraper.py          # Google Careers API
├── filters.py                 # Shared CS description filter logic
├── notifier.py                # Telegram alerts + daily digest
├── db.py                      # SQLite: init, dedup check, recent jobs query
├── config.yaml                # All targeting config — companies, locations, schedule
├── setup.sh                   # One-command server setup script
├── start.sh                   # Start the agent (activate venv + run)
├── update.sh                  # git pull + kill + restart for deployments
├── render.yaml                # Render.com worker service config
└── requirements.txt           # Python dependencies
```

---

## Setup

**1. Clone and install**
```bash
git clone https://github.com/omerbacher/Job-Alert-Agent.git
cd Job-Alert-Agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment variables**

Create a `.env` file:
```env
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

- **TELEGRAM_TOKEN** — create a bot via [@BotFather](https://t.me/BotFather)
- **TELEGRAM_CHAT_ID** — get your ID from [@userinfobot](https://t.me/userinfobot)

**3. Run**
```bash
python main.py
```

The agent runs all scrapers immediately on startup, then continues on schedule.

---

## Deployment

**Oracle Cloud / any Linux VPS — one-time setup**
```bash
bash <(curl -s https://raw.githubusercontent.com/omerbacher/Job-Alert-Agent/main/setup.sh)
cd Job-Alert-Agent
echo "TELEGRAM_TOKEN=..." > .env
echo "TELEGRAM_CHAT_ID=..." >> .env
mkdir -p logs
nohup bash start.sh > logs/agent.log 2>&1 &
```

**Deploy updates**
```bash
bash update.sh   # git pull + graceful restart
```

**systemd service (recommended)**
```ini
[Unit]
Description=Job Alert Agent
After=network.target

[Service]
WorkingDirectory=/root/Job-Alert-Agent
ExecStart=/root/Job-Alert-Agent/venv/bin/python main.py
Restart=always
EnvironmentFile=/root/Job-Alert-Agent/.env

[Install]
WantedBy=multi-user.target
```

---

## Configuration

All targeting is controlled via `config.yaml` — no code changes needed to add companies or locations:

```yaml
priority_companies:
  - "NVIDIA"
  - "Google"
  # ...

locations:
  - "Tel Aviv"
  - "Herzliya"
  # ...

hours_old: 72          # how far back to search on startup
hours_active_start: 8  # active window start
hours_active_end: 22   # active window end
```

---

## License

MIT
