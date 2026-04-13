import hashlib
import logging
import requests
import yaml

logger = logging.getLogger(__name__)

SEARCH_TEXT = "intern student"
REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]
BLOCKLIST = [
    "economics", "marketing", "finance", "accounting", "hr",
    "human resources", "legal", "sales", "supply chain", "logistics",
    "graphic", "content writer", "recruiter", "recruitment", "controller",
    "biology", "chemistry", "physics", "medical", "law", "mba",
]


def _load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _location_allowed(locations_text: str, allowed_locations: list[str]) -> bool:
    loc_lower = locations_text.lower()
    return any(loc.lower() in loc_lower for loc in allowed_locations)


def scrape_workday(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    global_locations: list[str] = config["locations"]
    workday_companies: list[dict] = config.get("workday_companies", [])

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for company_cfg in workday_companies:
        name: str = company_cfg["name"]
        url: str = company_cfg["url"]
        base_url: str = company_cfg["base_url"]
        allowed_locations: list[str] = company_cfg.get("special_locations") or global_locations

        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"limit": 20, "offset": 0, "searchText": SEARCH_TEXT},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Workday scrape failed for %s: %s", name, exc)
            continue

        data = response.json()
        postings = data.get("jobPostings", [])

        for posting in postings:
            title: str = posting.get("title", "") or ""
            external_path: str = posting.get("externalPath", "") or ""
            locations_text: str = posting.get("locationsText", "") or ""

            title_lower = title.lower()

            # Title must contain one of the required words
            if not any(w in title_lower for w in REQUIRED_TITLE_WORDS):
                continue

            # Blocklist filter
            if any(b in title_lower for b in BLOCKLIST):
                continue

            # CS description filter: Workday listing API returns no description,
            # so all jobs pass through (empty string → passes_cs_filter = True)

            # Location filter
            if not _location_allowed(locations_text, allowed_locations):
                continue

            job_url = base_url + external_path
            job_id = _make_id(title, name)

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append({
                "id": job_id,
                "title": title,
                "company": name,
                "location": locations_text,
                "url": job_url,
            })

        logger.info("Workday [%s]: %d jobs after filters", name, sum(1 for j in jobs if j["company"] == name))

    logger.info("Workday scrape total: %d unique jobs", len(jobs))
    return jobs
