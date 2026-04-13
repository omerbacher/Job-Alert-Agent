import hashlib
import logging
import requests
import yaml

logger = logging.getLogger(__name__)

REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]


def _load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_greenhouse(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    global_locations: list[str] = config["locations"]
    greenhouse_companies: list[dict] = config.get("greenhouse_companies", [])

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for company_cfg in greenhouse_companies:
        name: str = company_cfg["name"]
        company_id: str = company_cfg["id"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs?content=true"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Greenhouse scrape failed for %s: %s", name, exc)
            continue

        data = response.json()
        postings = data.get("jobs", [])

        for posting in postings:
            title: str = posting.get("title", "") or ""
            location: str = (posting.get("location") or {}).get("name", "") or ""
            job_url: str = posting.get("absolute_url", "") or ""

            title_lower = title.lower()

            # Title must contain one of the required words
            if not any(w in title_lower for w in REQUIRED_TITLE_WORDS):
                continue

            # Location filter: must contain at least one configured location
            location_lower = location.lower()
            if not any(loc.lower() in location_lower for loc in global_locations):
                continue

            job_id = _make_id(title, name)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append({
                "id": job_id,
                "title": title,
                "company": name,
                "location": location,
                "url": job_url,
            })

        logger.info("Greenhouse [%s]: fetched %d postings", name, len(postings))

    logger.info("Greenhouse scrape total: %d unique jobs after filters", len(jobs))
    return jobs
