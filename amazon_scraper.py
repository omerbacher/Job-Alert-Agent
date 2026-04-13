import hashlib
import logging
import requests
import yaml

logger = logging.getLogger(__name__)

REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]
BLOCKLIST = [
    "economics", "marketing", "finance", "accounting", "hr",
    "human resources", "legal", "sales", "supply chain", "logistics",
    "graphic", "content writer", "recruiter", "recruitment", "controller",
    "biology", "chemistry", "physics", "medical", "law", "mba",
]
BASE_URL = "https://www.amazon.jobs"
SEARCH_TERMS = ["intern", "student"]


def _load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_amazon(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for term in SEARCH_TERMS:
        try:
            response = requests.get(
                f"{BASE_URL}/en/search.json",
                params={
                    "base_query": term,
                    "country[]": "ISR",
                    "job_count": 100,
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Amazon scrape failed for term=%r: %s", term, exc)
            continue

        data = response.json()
        postings = data.get("jobs", [])
        logger.info("Amazon [%s]: %d results (hits=%s)", term, len(postings), data.get("hits", "?"))

        for posting in postings:
            title: str = posting.get("title", "") or ""
            location: str = posting.get("location", "") or ""
            job_path: str = posting.get("job_path", "") or ""

            title_lower = title.lower()

            # Title must contain one of the required words
            if not any(w in title_lower for w in REQUIRED_TITLE_WORDS):
                continue

            # Blocklist filter
            if any(b in title_lower for b in BLOCKLIST):
                continue

            job_url = BASE_URL + job_path
            job_id = _make_id(title, "Amazon")

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append({
                "id": job_id,
                "title": title,
                "company": "Amazon",
                "location": location,
                "url": job_url,
            })

    logger.info("Amazon scrape total: %d unique jobs after filters", len(jobs))
    return jobs
