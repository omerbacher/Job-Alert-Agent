import logging
import yaml
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from db import init_db, is_seen, save_job, get_recent_jobs
from scraper import scrape_priority, scrape_regular, scrape_defense
from workday_scraper import scrape_workday
from greenhouse_scraper import scrape_greenhouse
from google_scraper import scrape_google
from smartrecruiters_scraper import scrape_smartrecruiters
from amazon_scraper import scrape_amazon
from notifier import send_alert, send_digest

load_dotenv()

DRY_RUN = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    with open("config/config.yaml") as f:
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
                source=job.get("source", ""),
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


def run_workday():
    logger.info("[WORKDAY] Starting scan...")
    config = load_config()
    jobs = scrape_workday(config)
    for job in jobs:
        job["source"] = "Direct Career Site"
    _process_jobs(jobs, "WORKDAY")


def run_greenhouse():
    logger.info("[GREENHOUSE] Starting scan...")
    config = load_config()
    jobs = scrape_greenhouse(config)
    for job in jobs:
        job["source"] = "Direct Career Site"
    _process_jobs(jobs, "GREENHOUSE")


def run_google():
    logger.info("[GOOGLE] Starting scan...")
    config = load_config()
    jobs = scrape_google(config)
    for job in jobs:
        job["source"] = "Direct Career Site"
    _process_jobs(jobs, "GOOGLE")


def run_smartrecruiters():
    logger.info("[SMARTRECRUITERS] Starting scan...")
    config = load_config()
    jobs = scrape_smartrecruiters(config)
    for job in jobs:
        job["source"] = "Direct Career Site"
    _process_jobs(jobs, "SMARTRECRUITERS")


def run_amazon():
    logger.info("[AMAZON] Starting scan...")
    config = load_config()
    jobs = scrape_amazon(config)
    for job in jobs:
        job["source"] = "Direct Career Site"
    _process_jobs(jobs, "AMAZON")


def run_digest():
    logger.info("[DIGEST] Sending daily digest...")
    jobs = get_recent_jobs(hours=24)
    send_digest(jobs)
    logger.info("[DIGEST] Done — %d jobs in digest.", len(jobs))


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
    run_workday()
    run_greenhouse()
    run_google()
    run_smartrecruiters()
    run_amazon()

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

    # Workday: every 10 min during active hours
    scheduler.add_job(
        run_workday,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/10"),
        name="workday_scan",
    )

    # Greenhouse: every 30 min during active hours
    scheduler.add_job(
        run_greenhouse,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/30"),
        name="greenhouse_scan",
    )

    # Google Careers: every 10 min during active hours (priority)
    scheduler.add_job(
        run_google,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/10"),
        name="google_scan",
    )

    # SmartRecruiters: every 30 min during active hours
    scheduler.add_job(
        run_smartrecruiters,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/30"),
        name="smartrecruiters_scan",
    )

    # Amazon: every 10 min during active hours (priority)
    scheduler.add_job(
        run_amazon,
        trigger=CronTrigger(hour=f"{start_hour}-{end_hour - 1}", minute="*/10"),
        name="amazon_scan",
    )

    # Daily digest at 08:00
    scheduler.add_job(
        run_digest,
        trigger=CronTrigger(hour=8, minute=0),
        name="daily_digest",
    )

    logger.info(
        "Schedulers started — priority/workday/google every 10min, regular/greenhouse every 30min (%02d:00-%02d:00), defense daily at 09:00.",
        start_hour,
        end_hour,
    )
    scheduler.start()
