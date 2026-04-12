import hashlib
import logging
import yaml
from jobspy import scrape_jobs

logger = logging.getLogger(__name__)


def _load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str, url: str) -> str:
    raw = f"{title}|{company}|{url}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    keywords: list[str] = config["keywords"]
    companies: list[str] = [c.lower() for c in config["companies"]]
    locations: list[str] = config["locations"]
    max_results: int = config["max_results_per_search"]
    hours_old: int = config["hours_old"]

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for keyword in keywords:
        for location in locations:
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed"],
                    search_term=keyword,
                    location=location,
                    results_wanted=max_results,
                    hours_old=hours_old,
                    country_indeed="Israel",
                )
            except Exception as exc:
                logger.warning("Scrape failed for keyword=%r location=%r: %s", keyword, location, exc)
                continue

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                title: str = str(row.get("title", "") or "")
                company: str = str(row.get("company", "") or "")
                location_val: str = str(row.get("location", "") or "")
                url: str = str(row.get("job_url", "") or "")
                description: str = str(row.get("description", "") or "")

                title_lower = title.lower()

                # Hard requirement: title must contain one of these words
                REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]
                if not any(w in title_lower for w in REQUIRED_TITLE_WORDS):
                    continue

                # Strict company filter: must exactly match a company from config
                if company.lower() not in companies:
                    continue

                # Location filter: must contain at least one configured location
                location_lower = location_val.lower()
                if not any(loc.lower() in location_lower for loc in locations):
                    continue

                job_id = _make_id(title, company, url)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": location_val,
                    "url": url,
                    "description": description,
                })

    logger.info("Scraper found %d unique candidate jobs", len(jobs))
    return jobs
