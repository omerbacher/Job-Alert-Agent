import asyncio
import logging
import os
import re
from collections import defaultdict
from datetime import datetime

from telegram import Bot

logger = logging.getLogger(__name__)

_REQUIREMENT_KEYWORDS = (
    "degree", "student", "pursuing", "experience", "knowledge",
    "proficiency", "familiar", "background", "minimum", "required",
    "must", "ability", "skill", "year", "gpa", "average", "fluent",
    "understanding", "passion", "motivated", "advantage",
)

_GENERIC_TITLES = {"student", "intern"}

# Unambiguous job-specific URL segments
_VALID_JOB_PATH_SEGMENTS = (
    "/job/", "/jobs/", "/position/", "/posting/", "/opening/", "/view/",
    "/requisition/", "/apply/", "/gh_jid=", "?gh_jid", "lever.co/",
    "greenhouse.io/", "smartrecruiters.com/", "myworkdayjobs.com/",
    "ashbyhq.com/", "amazon.jobs/en/jobs/",
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _fix_url(url: str) -> str:
    """Attempt to normalise common malformed URLs before validation."""
    if url.startswith("//"):
        return "https:" + url
    return url


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    url = _fix_url(url)
    if not url.startswith(("http://", "https://")):
        return False
    full = url.lower()
    # /careers/ is only accepted when something meaningful follows it
    if "/careers/" in full:
        idx = full.index("/careers/")
        remainder = full[idx + len("/careers/"):].lstrip("/")
        if len(remainder) > 2:
            return True
    return any(seg in full for seg in _VALID_JOB_PATH_SEGMENTS)


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

    # Split on newlines first; also split on ". " for dense single-line descriptions
    raw_lines: list[str] = []
    for segment in re.split(r"\r\n|\n|\r", description):
        if ". " in segment and len(segment) > 200:
            raw_lines.extend(re.split(r"\.\s+", segment))
        else:
            raw_lines.append(segment)

    _STRIP_PREFIX = re.compile(r"^[\s•·\-–\*·]+|\s*\d+\.\s*")

    def _clean(line: str) -> str:
        return _STRIP_PREFIX.sub("", line).strip()

    bullets: list[str] = []
    fallback_lines: list[str] = []

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        cleaned = _clean(line)
        if not cleaned:
            continue

        # Collect non-empty lines for fallback
        if len(fallback_lines) < 3 and 15 <= len(cleaned) <= 150:
            fallback_lines.append(cleaned)

        # Keyword match for requirements section
        line_lower = line.lower()
        if any(kw in line_lower for kw in _REQUIREMENT_KEYWORDS):
            if 15 <= len(cleaned) <= 150:
                bullets.append(cleaned)
        if len(bullets) == max_bullets:
            break

    return bullets if bullets else fallback_lines


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
    url = _fix_url(url)
    if not _is_valid_url(url):
        logger.warning("Skipping alert — invalid URL: %r (title=%r)", url, title)
        return False

    try:
        token = os.environ["TELEGRAM_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

        logger.info("Description length: %d", len(description))
        logger.info("Description preview: %s", description[:200])
        job_type = _infer_job_type(title, description)
        bullets = _extract_bullets(description)
        logger.info("Bullets extracted: %s", bullets)

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
            await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)

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
            text = f"📋 Daily Digest — {date_str}\nNo new CS student roles found today. Bot is running normally. ✅"
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
            await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)

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
