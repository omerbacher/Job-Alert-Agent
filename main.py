import logging
import yaml
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from db import init_db, is_seen, save_job
from scraper import scrape
from notifier import send_alert

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def run_scan():
    config = load_config()

    logger.info("Starting job scan...")
    jobs = scrape(config)

    new_count = 0

    for job in jobs:
        job_id = job["id"]

        if is_seen(job_id):
            continue

        new_count += 1
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

    logger.info("Scan complete — %d new jobs found and alerted.", new_count)


if __name__ == "__main__":
    init_db()

    config = load_config()
    interval = config["check_interval_minutes"]
    start_hour = config["hours_active_start"]
    end_hour = config["hours_active_end"]

    # Run once immediately on startup
    run_scan()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_scan,
        trigger=CronTrigger(
            hour=f"{start_hour}-{end_hour - 1}",
            minute=f"*/{interval}",
        ),
    )

    logger.info(
        "Scheduler started — scanning every %d min between %02d:00 and %02d:00.",
        interval,
        start_hour,
        end_hour,
    )
    scheduler.start()
