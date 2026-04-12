import logging
import yaml
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from db import init_db, is_seen, save_job
from scraper import scrape_priority, scrape_regular, scrape_defense
from notifier import send_alert

load_dotenv()

DRY_RUN = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _process_jobs(jobs: list[dict], tier: str):
    new_count = 0
    for job in jobs:
        job_id = job["id"]
        if is_seen(job_id):
            continue

        new_count += 1

        if DRY_RUN:
            logger.info("[DRY RUN][%s] %s @ %s | %s | %s", tier, job['title'], job['company'], job['location'], job['url'])
        else:
            send_alert(
                title=job["title"],
                company=job["company"],
                location=job["location"],
                url=job["url"],
            )

        save_job(
            job_id=job_id,
            title=job["title"],
            company=job["company"],
            location=job["location"],
            url=job["url"],
            score=0,
        )

    logger.info("[%s] Scan complete — %d new jobs found.", tier, new_count)


def run_priority():
    logger.info("[PRIORITY] Starting scan...")
    config = load_config()
    jobs = scrape_priority(config)
    _process_jobs(jobs, "PRIORITY")


def run_regular():
    logger.info("[REGULAR] Starting scan...")
    config = load_config()
    jobs = scrape_regular(config)
    _process_jobs(jobs, "REGULAR")


def run_defense():
    logger.info("[DEFENSE] Starting scan...")
    config = load_config()
    jobs = scrape_defense(config)
    _process_jobs(jobs, "DEFENSE")


if __name__ == "__main__":
    init_db()

    config = load_config()
    start_hour = config["hours_active_start"]
    end_hour = config["hours_active_end"]

    if DRY_RUN:
        logger.info("DRY RUN mode enabled — no Telegram alerts will be sent.")

    # Run all tiers immediately on startup
    run_priority()
    run_regular()
    run_defense()

    scheduler = BlockingScheduler()

    # Priority: every 10 min during active hours
    scheduler.add_job(
        run_priority,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/10"),
        name="priority_scan",
    )

    # Regular: every 30 min during active hours
    scheduler.add_job(
        run_regular,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/30"),
        name="regular_scan",
    )

    # Defense: once daily at 09:00
    scheduler.add_job(
        run_defense,
        trigger=CronTrigger(hour=9, minute=0),
        name="defense_scan",
    )

    logger.info(
        "Schedulers started — priority every 10min, regular every 30min (%02d:00-%02d:00), defense daily at 09:00.",
        start_hour,
        end_hour,
    )
    scheduler.start()
