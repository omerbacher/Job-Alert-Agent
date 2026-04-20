import hashlib
import logging
import yaml
from jobspy import scrape_jobs
from filters import passes_cs_filter, passes_title_filter, passes_description_filter

logger = logging.getLogger(__name__)

SEARCH_TERMS = ["intern", "internship", "student"]
GENERAL_SEARCH_TERMS = ["intern Israel", "student Israel", "internship Israel"]
REQUIRED_TITLE_WORDS = ["intern", "internship", "student"]
BLOCKLIST = [
    "economics", "marketing", "finance", "accounting", "hr",
    "human resources", "legal", "sales", "supply chain", "logistics",
    "graphic", "content writer", "recruiter", "recruitment", "controller",
    "biology", "chemistry", "physics", "medical", "law", "mba",
]
MAX_RESULTS = 50


def _load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


def _make_id(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _scrape_for_companies(companies: list[str], locations: list[str], hours_old: int) -> list[dict]:
    companies_lower = [c.lower() for c in companies]
    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for term in SEARCH_TERMS:
        for location in locations:
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed"],
                    search_term=term,
                    location=location,
                    results_wanted=MAX_RESULTS,
                    hours_old=hours_old,
                    country_indeed="Israel",
                )
            except Exception as exc:
                logger.warning("Scrape failed for term=%r location=%r: %s", term, location, exc)
                continue

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                title: str = str(row.get("title", "") or "")
                company: str = str(row.get("company", "") or "")
                location_val: str = str(row.get("location", "") or "")
                url: str = str(row.get("job_url", "") or "")

                title_lower = title.lower()

                # Title must pass CS relevance + intern/student check
                if not passes_title_filter(title, company):
                    continue

                # Blocklist filter
                if any(b in title_lower for b in BLOCKLIST):
                    continue

                # CS description filter
                description: str = str(row.get("description", "") or "")
                if not passes_cs_filter(description):
                    continue

                # Description-based CS relevance filter
                if not passes_description_filter(title, description):
                    continue

                # Strict company filter: must be in this tier's list
                if company.lower() not in companies_lower:
                    continue

                # Location filter: must contain at least one configured location
                location_lower = location_val.lower()
                if not any(loc.lower() in location_lower for loc in locations):
                    continue

                job_id = _make_id(title, company)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": location_val,
                    "url": url,
                })

    return jobs


def scrape_priority(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()
    jobs = _scrape_for_companies(
        companies=config["priority_companies"],
        locations=config["locations"],
        hours_old=config["hours_old"],
    )
    logger.info("Priority scrape found %d unique jobs", len(jobs))
    return jobs


def scrape_regular(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()
    jobs = _scrape_for_companies(
        companies=config["regular_companies"],
        locations=config["locations"],
        hours_old=config["hours_old"],
    )
    logger.info("Regular scrape found %d unique jobs", len(jobs))
    return jobs


def _scrape_no_company_filter(search_terms: list[str], locations: list[str], hours_old: int, allowed_companies: list[str]) -> list[dict]:
    allowed_lower = [c.lower() for c in allowed_companies]
    seen_ids: set[str] = set()
    jobs: list[dict] = []

    for term in search_terms:
        try:
            df = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=term,
                location="Israel",
                results_wanted=MAX_RESULTS,
                hours_old=hours_old,
                country_indeed="Israel",
            )
        except Exception as exc:
            logger.warning("General scrape failed for term=%r: %s", term, exc)
            continue

        if df is None or df.empty:
            continue

        for _, row in df.iterrows():
            title: str = str(row.get("title", "") or "")
            company: str = str(row.get("company", "") or "")
            location_val: str = str(row.get("location", "") or "")
            url: str = str(row.get("job_url", "") or "")

            title_lower = title.lower()

            if not passes_title_filter(title, company):
                continue

            if any(b in title_lower for b in BLOCKLIST):
                continue

            description: str = str(row.get("description", "") or "")
            if not passes_cs_filter(description):
                continue

            # Description-based CS relevance filter
            if not passes_description_filter(title, description):
                continue

            # Strict company filter: must be in allowed list
            if company.lower() not in allowed_lower:
                continue

            location_lower = location_val.lower()
            if not any(loc.lower() in location_lower for loc in locations):
                continue

            job_id = _make_id(title, company)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append({
                "id": job_id,
                "title": title,
                "company": company,
                "location": location_val,
                "url": url,
            })

    return jobs


def scrape_general(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()
    allowed = config["priority_companies"] + config["regular_companies"]
    jobs = _scrape_no_company_filter(
        search_terms=GENERAL_SEARCH_TERMS,
        locations=config["locations"],
        hours_old=config["hours_old"],
        allowed_companies=allowed,
    )
    logger.info("General scrape found %d unique jobs", len(jobs))
    return jobs


def scrape_defense(config: dict | None = None) -> list[dict]:
    if config is None:
        config = _load_config()
    jobs = _scrape_for_companies(
        companies=config["defense_companies"],
        locations=config["locations"],
        hours_old=config["hours_old"],
    )
    logger.info("Defense scrape found %d unique jobs", len(jobs))
    return jobs
