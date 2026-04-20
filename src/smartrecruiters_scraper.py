import hashlib
import logging
import requests
import yaml
from filters import passes_title_filter

logger = logging.getLogger(__name__)

REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]
BLOCKLIST = [
    "economics", "marketing", "finance", "accounting", "hr",
    "human resources", "legal", "sales", "supply chain", "logistics",
    "graphic", "content writer", "recruiter", "recruitment", "controller",
    "biology", "chemistry", "physics", "medical", "law", "mba",
]


def _load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def scrape_smartrecruiters(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    global_locations: list[str] = config["locations"]
    sr_companies: list[dict] = config.get("smartrecruiters_companies", [])

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for company_cfg in sr_companies:
        name: str = company_cfg["name"]
        identifier: str = company_cfg["id"]
        url = f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings?limit=100"

        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("SmartRecruiters scrape failed for %s: %s", name, exc)
            continue

        data = response.json()
        postings = data.get("content", [])
        logger.info("SmartRecruiters [%s]: %d total postings", name, data.get("totalFound", 0))

        for posting in postings:
            title: str = posting.get("name", "") or ""
            location_obj = posting.get("location") or {}
            full_location: str = location_obj.get("fullLocation", "") or ""
            job_id_sr: str = str(posting.get("id", ""))

            title_lower = title.lower()

            # Title must pass CS relevance + intern/student check
            if not passes_title_filter(title):
                continue

            # Blocklist filter
            if any(b in title_lower for b in BLOCKLIST):
                continue

            # CS description filter: SmartRecruiters listing API returns no description,
            # so all jobs pass through (empty string → passes_cs_filter = True)

            # Location filter
            location_lower = full_location.lower()
            if not any(loc.lower() in location_lower for loc in global_locations):
                continue

            job_url = f"https://jobs.smartrecruiters.com/{identifier}/{job_id_sr}"
            job_id = _make_id(title, name)

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append({
                "id": job_id,
                "title": title,
                "company": name,
                "location": full_location,
                "url": job_url,
            })

    logger.info("SmartRecruiters scrape total: %d unique jobs after filters", len(jobs))
    return jobs
