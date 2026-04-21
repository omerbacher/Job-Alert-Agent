import hashlib
import logging
import requests
import yaml
from filters import passes_title_filter, is_cs_relevant, passes_location_filter

logger = logging.getLogger(__name__)

SEARCH_TEXT = "intern student"
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



def _extract_description(posting: dict) -> str:
    """Pull whatever description text the Workday listing API returns."""
    parts = []
    for field in ("jobDescription", "description", "briefDescription",
                  "shortDescription", "jobSummary"):
        val = posting.get(field)
        if isinstance(val, dict):
            val = val.get("descriptor") or val.get("text") or ""
        if val and isinstance(val, str):
            parts.append(val.strip())
    return "\n".join(parts)


def scrape_workday(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()

    workday_companies: list[dict] = config.get("workday_companies", [])

    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for company_cfg in workday_companies:
        name: str     = company_cfg["name"]
        url: str      = company_cfg["url"]
        base_url: str = company_cfg["base_url"]

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
            title: str         = posting.get("title", "") or ""
            external_path: str = posting.get("externalPath", "") or ""
            locations_text: str = posting.get("locationsText", "") or ""
            description: str   = _extract_description(posting)

            title_lower = title.lower()

            # Stage 1: title must contain intern/internship/student
            if not passes_title_filter(title):
                continue

            # Blocklist
            if any(b in title_lower for b in BLOCKLIST):
                continue

            # Location filter
            if not passes_location_filter(locations_text):
                continue

            # Stage 2: CS relevance (title fallback when description absent)
            if not is_cs_relevant(title, description):
                continue

            # Build job URL: base_url/en-US/{site_name}{externalPath} verbatim
            site_name = url.split("/")[-2]
            job_url   = f"{base_url}/en-US/{site_name}{external_path}"
            job_id    = _make_id(title, name)

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            logger.info("Workday [%s] job URL: %s", name, job_url)
            logger.info(f"Job description length: {len(description)}")
            jobs.append({
                "id": job_id,
                "title": title,
                "company": name,
                "location": locations_text,
                "url": job_url,
                "description": description,
            })

        logger.info("Workday [%s]: %d jobs after filters", name, sum(1 for j in jobs if j["company"] == name))

    logger.info("Workday scrape total: %d unique jobs", len(jobs))
    return jobs
