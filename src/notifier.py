import asyncio
import logging
import os
import re
from datetime import datetime

from telegram import Bot

logger = logging.getLogger(__name__)


def _extract_bullets(description: str, max_bullets: int = 3) -> list[str]:
    """Extract up to max_bullets requirement lines from a job description."""
    if not description or len(description) < 50:
        return []

    lines = re.split(r"[\n•·\-–]", description)
    bullets = []
    for line in lines:
        line = line.strip()
        # Keep lines that look like requirements (10–120 chars, not just a header)
        if 10 <= len(line) <= 120 and not line.endswith(":"):
            bullets.append(line)
        if len(bullets) == max_bullets:
            break
    return bullets


def send_alert(title: str, company: str, location: str, url: str, source: str = "", description: str = ""):
    try:
        token = os.environ["TELEGRAM_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

        text = (
            "🚨 New Student Job Match!\n"
            f"📌 {title}\n"
            f"🏢 {company}\n"
            f"📍 {location}\n"
            f"🔗 {url}"
        )
        if source:
            text += f"\n📡 Source: {source}"

        bullets = _extract_bullets(description)
        if bullets:
            text += "\n📋 Key Requirements:\n" + "\n".join(f"  • {b}" for b in bullets)

        async def _send():
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=text)

        asyncio.run(_send())
        logger.info("Alert sent: %s at %s", title, company)
    except Exception as exc:
        logger.error("Failed to send Telegram alert for %r: %s", title, exc)


def send_digest(jobs: list[dict]):
    try:
        from collections import defaultdict

        token = os.environ["TELEGRAM_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

        date_str = datetime.now().strftime("%d/%m/%Y")

        if not jobs:
            text = "📋 Daily Digest: No new CS roles found today."
        else:
            by_company: dict[str, list[dict]] = defaultdict(list)
            for job in jobs:
                by_company[job["company"]].append(job)

            lines = [
                f"📋 Daily Job Digest — {date_str}",
                f"{len(jobs)} new CS student roles in the last 24 hours:\n",
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
