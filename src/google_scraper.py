import hashlib
import logging
import requests
import yaml

logger = logging.getLogger(__name__)

REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]
GOOGLE_CAREERS_URL = "https://careers.google.com/api/v3/search/"


def _load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_google(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    try:
        response = requests.get(
            GOOGLE_CAREERS_URL,
            params={"q": "intern student", "location": "Israel", "page_size": 20},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Google Careers scrape failed: %s", exc)
        return jobs

    data = response.json()
    postings = data.get("jobs", [])

    for posting in postings:
        title: str = posting.get("title", "") or ""
        locations: list = posting.get("locations", []) or []
        apply_url: str = posting.get("apply_url", "") or ""

        title_lower = title.lower()

        # Title must contain one of the required words
        if not any(w in title_lower for w in REQUIRED_TITLE_WORDS):
            continue

        location_str = ", ".join(locations) if locations else ""

        job_id = _make_id(title, "Google")
        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        jobs.append({
            "id": job_id,
            "title": title,
            "company": "Google",
            "location": location_str,
            "url": apply_url,
        })

    logger.info("Google Careers scrape: %d unique jobs after filters", len(jobs))
    return jobs
