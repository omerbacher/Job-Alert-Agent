import asyncio
import logging
import os
import re
from collections import defaultdict
from datetime import datetime

from telegram import Bot

logger = logging.getLogger(__name__)

_REQUIREMENT_KEYWORDS = (
    "degree", "pursuing", "b.sc", "m.sc", "knowledge",
    "proficiency", "minimum", "required", "must", "skill",
    "experience", "familiarity", "background", "advantage",
    "fluent", "gpa",
)

_DEPRIORITIZE_PREFIXES = (
    "build", "develop", "design", "implement",
    "create", "manage", "lead", "responsible",
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


_STRIP_PREFIX = re.compile(r"^[\s•·\-–\*·]*(?:\d+[.):\s]+)?\s*")


def _extract_bullets(description: str, max_bullets: int = 4) -> list[str]:
    if not description or len(description) < 50:
        return []

    def _clean(line: str) -> str:
        return _STRIP_PREFIX.sub("", line).strip()

    # Step 1: split by newlines
    newline_segments = [s.strip() for s in re.split(r"\r\n|\n|\r", description) if s.strip()]

    # Step 2: if fewer than 3 lines, the description is a dense paragraph — split by sentences
    if len(newline_segments) >= 3:
        segments = newline_segments
    else:
        segments = [s.strip() for s in re.split(r"\.\s+", description) if s.strip()]

    preferred: list[str] = []
    deprioritized: list[str] = []

    for seg in segments:
        cleaned = _clean(seg)
        if not cleaned or len(cleaned) < 15 or len(cleaned) > 200:
            continue

        lower = cleaned.lower()
        if any(lower.startswith(p) for p in _DEPRIORITIZE_PREFIXES):
            deprioritized.append(cleaned)
        elif any(kw in lower for kw in _REQUIREMENT_KEYWORDS):
            preferred.append(cleaned)

        if len(preferred) == max_bullets:
            break

    combined = preferred + deprioritized
    return combined[:max_bullets]


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
    department: str = "",
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

        bullets = _extract_bullets(description)
        logger.info("Bullets extracted: %s", bullets)

        lines = [
            "🚨 New Job Match!",
            "",
            f"📌 {title} / {company}",
            f"📍 {location}" + (f" | {department}" if department else ""),
        ]

        if bullets:
            lines += ["", "📋 Requirements:"]
            lines += [f"- {b}" for b in bullets]

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
