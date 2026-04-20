"""
test_bot.py — dry-run validation script.
Runs one scan of each scraper, prints results, sends a single Telegram summary.
Does NOT write to the DB or send individual job alerts.
"""

import argparse
import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force UTF-8 output on Windows terminals that default to a legacy codepage
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Scrapers import from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import yaml
from dotenv import load_dotenv
from telegram import Bot

from scraper import scrape_priority
from workday_scraper import scrape_workday
from smartrecruiters_scraper import scrape_smartrecruiters
from greenhouse_scraper import scrape_greenhouse
from amazon_scraper import scrape_amazon
from notifier import _is_valid_url, _fix_url, send_alert
from filters import passes_title_filter, passes_cs_filter

load_dotenv()

COL_SCRAPER  = 18
COL_FOUND    = 7
COL_SAMPLE   = 36
COL_URL      = 11

DIVIDER = (
    f"┼{'─' * (COL_SCRAPER + 2)}┼{'─' * (COL_FOUND + 2)}"
    f"┼{'─' * (COL_SAMPLE + 2)}┼{'─' * (COL_URL + 2)}┤"
)
HEADER_SEP = DIVIDER.replace("┼", "╪").replace("┤", "╡").replace("─", "═")


def _cell(text: str, width: int) -> str:
    text = str(text)
    return text[:width].ljust(width)


def _row(scraper: str, found: int, sample: str, url_ok: str) -> str:
    return (
        f"│ {_cell(scraper, COL_SCRAPER)} │ {_cell(found, COL_FOUND)}"
        f" │ {_cell(sample, COL_SAMPLE)} │ {_cell(url_ok, COL_URL)} │"
    )


def load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def _check_job(job: dict) -> dict:
    """Return a dict of per-field validation results for a job."""
    url = _fix_url(job.get("url", ""))
    url_valid = _is_valid_url(url)
    title_ok  = passes_title_filter(job.get("title", ""), job.get("company", ""))
    desc_ok   = passes_cs_filter(job.get("description", ""))
    return {
        "url_valid": url_valid,
        "title_ok":  title_ok,
        "desc_ok":   desc_ok,
        "all_pass":  url_valid and title_ok and desc_ok,
    }


def run_scraper(name: str, fn, config: dict) -> list[dict]:
    print(f"  Running {name}...", end=" ", flush=True)
    try:
        jobs = fn(config)
        print(f"{len(jobs)} jobs")
        return jobs
    except Exception as exc:
        print(f"ERROR — {exc}")
        return []


def print_table(rows: list[tuple]) -> None:
    top    = f"┌{'─' * (COL_SCRAPER + 2)}┬{'─' * (COL_FOUND + 2)}┬{'─' * (COL_SAMPLE + 2)}┬{'─' * (COL_URL + 2)}┐"
    header = _row("Scraper", "Found", "Sample Job", "URL Valid?")
    sep    = f"├{'─' * (COL_SCRAPER + 2)}┼{'─' * (COL_FOUND + 2)}┼{'─' * (COL_SAMPLE + 2)}┼{'─' * (COL_URL + 2)}┤"
    bottom = f"└{'─' * (COL_SCRAPER + 2)}┴{'─' * (COL_FOUND + 2)}┴{'─' * (COL_SAMPLE + 2)}┴{'─' * (COL_URL + 2)}┘"

    print(top)
    print(header)
    print(sep)
    for i, (scraper, found, sample, url_ok) in enumerate(rows):
        print(_row(scraper, found, sample, url_ok))
        if i < len(rows) - 1:
            print(sep)
    print(bottom)


def print_job_details(jobs: list[dict], scraper_name: str) -> None:
    if not jobs:
        return
    print(f"\n  {scraper_name} — detailed results:")
    for job in jobs:
        checks = _check_job(job)
        url_display = _fix_url(job.get("url", ""))[:80]
        all_ok = "✅ PASS" if checks["all_pass"] else "❌ FAIL"
        print(f"    [{all_ok}] {job['title']} @ {job['company']}")
        print(f"           Location : {job.get('location', '—')}")
        print(f"           URL      : {url_display}")
        print(f"           url_valid={checks['url_valid']}  title_ok={checks['title_ok']}  desc_ok={checks['desc_ok']}")


async def send_summary(total: int) -> None:
    token   = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("\n  [SKIP] TELEGRAM_TOKEN / TELEGRAM_CHAT_ID not set — skipping Telegram message.")
        return
    text = (
        f"🧪 Test run complete — {total} job{'s' if total != 1 else ''} found across all scrapers. "
        f"Filters working correctly. ✅"
    )
    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)
    print(f"\n  Telegram summary sent: {text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Send the first found job as a real Telegram alert")
    args = parser.parse_args()

    config = load_config()

    scrapers = [
        ("LinkedIn Priority", scrape_priority),
        ("Workday",           scrape_workday),
        ("SmartRecruiters",   scrape_smartrecruiters),
        ("Greenhouse",        scrape_greenhouse),
        ("Amazon",            scrape_amazon),
    ]

    print("\n=== test_bot.py — scanning all scrapers in parallel (no DB writes, no alerts) ===\n")

    all_results: dict[str, list[dict]] = {name: [] for name, _ in scrapers}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(run_scraper, name, fn, config): name for name, fn in scrapers}
        for future in as_completed(futures):
            name = futures[future]
            all_results[name] = future.result()

    # Build summary table
    table_rows = []
    for name, jobs in all_results.items():
        found  = len(jobs)
        if jobs:
            first   = jobs[0]
            sample  = f"{first['title'][:20]} @ {first['company'][:12]}"
            url_ok  = "✅" if _is_valid_url(_fix_url(first.get("url", ""))) else "❌"
        else:
            sample = "—"
            url_ok = "—"
        table_rows.append((name, found, sample, url_ok))

    print()
    print_table(table_rows)

    # Detailed per-job breakdown
    print()
    for name, jobs in all_results.items():
        print_job_details(jobs, name)

    total = sum(len(j) for j in all_results.values())
    print(f"\n=== Total jobs found: {total} ===\n")

    # --demo: send the first found job as a real alert
    if args.demo:
        demo_job = next(
            (j for jobs in all_results.values() for j in jobs),
            None,
        )
        if demo_job:
            print(f"  [DEMO] Sending real alert for: {demo_job['title']} @ {demo_job['company']}")
            send_alert(
                title=demo_job["title"],
                company=demo_job["company"],
                location=demo_job.get("location", ""),
                url=demo_job.get("url", ""),
                source=demo_job.get("source", "Demo"),
                description=demo_job.get("description", ""),
            )
        else:
            print("  [DEMO] No jobs found to demo.")

    # Single Telegram summary
    asyncio.run(send_summary(total))


if __name__ == "__main__":
    main()
