import asyncio
import logging
import os
import re
from collections import defaultdict
from datetime import datetime

from telegram import Bot

logger = logging.getLogger(__name__)

_REQUIREMENT_PREFIXES = (
    "•", "-", "student", "experience", "knowledge", "minimum",
    "bachelor", "pursuing", "degree",
)

_GENERIC_TITLES = {"student", "intern"}

_VALID_JOB_PATH_SEGMENTS = (
    "/job/", "/jobs/", "/position/", "/posting/", "/opening/",
    "/requisition/", "/apply/", "/gh_jid=", "?gh_jid", "lever.co/",
    "greenhouse.io/", "smartrecruiters.com/", "myworkdayjobs.com/",
    "ashbyhq.com/", "careers/job", "careers/",
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _is_valid_url(url: str) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False
    # Must have a path beyond a bare homepage
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        query = parsed.query
        if not path and not query:
            return False  # bare domain
        full = url.lower()
        return any(seg in full for seg in _VALID_JOB_PATH_SEGMENTS)
    except Exception:
        return False


def _is_valid_title(title: str) -> bool:
    if not title or len(title.strip()) < 5:
        return False
    words = title.lower().split()
    if len(words) == 1 and words[0] in _GENERIC_TITLES:
        return False
    return True


def _extract_bullets(description: str, max_bullets: int = 4) -> list[str]:
    if not description or len(description) < 50:
        return []

    bullets = []
    for line in description.splitlines():
        line = line.strip()
        if not line:
            continue
        line_lower = line.lower()
        if any(line_lower.startswith(p) for p in _REQUIREMENT_PREFIXES):
            # Clean leading bullet/dash chars
            cleaned = re.sub(r"^[•·\-–\*]\s*", "", line).strip()
            if 10 <= len(cleaned) <= 150:
                bullets.append(cleaned)
        if len(bullets) == max_bullets:
            break
    return bullets


def _infer_job_type(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    if any(w in text for w in ("hardware", "fpga", "pcb", "embedded", "vlsi", "rtl", "asic")):
        return "Hardware"
    if any(w in text for w in ("machine learning", "ml ", "deep learning", "ai ", "data science", "nlp")):
        return "ML / AI"
    if any(w in text for w in ("data", "analytics", "bi ", "business intelligence")):
        return "Data"
    if any(w in text for w in ("security", "cyber", "infosec", "penetration", "soc ")):
        return "Cybersecurity"
    if any(w in text for w in ("finance", "accounting", "economics", "financial")):
        return "Finance"
    if any(w in text for w in ("devops", "sre ", "infrastructure", "cloud", "kubernetes", "docker")):
        return "DevOps / Cloud"
    if any(w in text for w in ("frontend", "front-end", "react", "vue", "angular", "ui ", "ux ")):
        return "Frontend"
    if any(w in text for w in ("backend", "back-end", "server", "api ", "microservice")):
        return "Backend"
    if any(w in text for w in ("fullstack", "full-stack", "full stack")):
        return "Full-Stack"
    if any(w in text for w in ("software", "developer", "engineer", "programming", "coding")):
        return "Software"
    if any(w in text for w in ("research", "phd", "academic", "scientist")):
        return "Research"
    return "Engineering"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_alert(
    title: str,
    company: str,
    location: str,
    url: str,
    source: str = "",
    description: str = "",
) -> bool:
    """Send a single job alert. Returns False if the job is filtered out."""
    if not _is_valid_title(title):
        logger.warning("Skipping alert — invalid title: %r", title)
        return False
    if not _is_valid_url(url):
        logger.warning("Skipping alert — invalid URL: %r (title=%r)", url, title)
        return False

    try:
        token = os.environ["TELEGRAM_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

        job_type = _infer_job_type(title, description)
        bullets = _extract_bullets(description)

        lines = [
            "🚨 New Job Match!",
            "",
            f"📌 {title} / {company}",
            f"| {job_type}",
            f"📍 {location}",
        ]

        if bullets:
            lines += ["", "📋 Requirements:"]
            lines += [f"• {b}" for b in bullets]

        lines += ["", f"🔗 {url}"]
        if source:
            lines.append(f"📡 Source: {source}")

        text = "\n".join(lines)

        async def _send():
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=text)

        asyncio.run(_send())
        logger.info("Alert sent: %s at %s", title, company)
        return True
    except Exception as exc:
        logger.error("Failed to send Telegram alert for %r: %s", title, exc)
        return False


def send_digest(jobs: list[dict]):
    """Send the daily digest. Always sends, even when jobs list is empty."""
    try:
        token = os.environ["TELEGRAM_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

        date_str = datetime.now().strftime("%d/%m/%Y")

        if not jobs:
            text = f"📋 Daily Digest — {date_str}\nNo new CS student roles found in the last 24 hours."
        else:
            by_company: dict[str, list[dict]] = defaultdict(list)
            for job in jobs:
                by_company[job["company"]].append(job)

            lines = [
                f"📋 Daily Job Digest — {date_str}",
                f"{len(jobs)} new CS student role{'s' if len(jobs) != 1 else ''} in the last 24 hours:\n",
            ]
            for company, company_jobs in by_company.items():
                count = len(company_jobs)
                lines.append(f"🏢 {company} ({count} job{'s' if count > 1 else ''})")
                for job in company_jobs:
                    lines.append(f"• {job['title']} — {job['location']}")
                    lines.append(f"  🔗 {job['url']}")
                lines.append("")

            text = "\n".join(lines).rstrip()

        async def _send():
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=text)

        asyncio.run(_send())
        logger.info("Digest sent: %d jobs", len(jobs))
    except Exception as exc:
        logger.error("Failed to send digest: %s", exc)


def test_digest():
    """Send a test digest with fake jobs to verify Telegram delivery."""
    fake_jobs = [
        {
            "title": "Software Engineer Intern",
            "company": "Wiz",
            "location": "Tel Aviv",
            "url": "https://boards.greenhouse.io/wizinc/jobs/123456",
        },
        {
            "title": "Data Science Student",
            "company": "Taboola",
            "location": "Tel Aviv",
            "url": "https://boards.greenhouse.io/taboola/jobs/654321",
        },
    ]
    logger.info("Running test_digest...")
    send_digest(fake_jobs)
    logger.info("test_digest complete.")
