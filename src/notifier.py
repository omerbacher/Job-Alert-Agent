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
        token = os.environ["TELEGRAM_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]

        date_str = datetime.now().strftime("%d/%m/%Y")

        if not jobs:
            text = "📋 Daily Digest: No new jobs found in the last 24 hours."
        else:
            lines = [f"📋 Daily Digest — {date_str}", f"Found {len(jobs)} new student jobs:\n"]
            for i, job in enumerate(jobs, 1):
                lines.append(f"{i}. {job['title']} at {job['company']} — {job['location']}")
                lines.append(f"🔗 {job['url']}\n")
            text = "\n".join(lines)

        async def _send():
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=text)

        asyncio.run(_send())
        logger.info("Digest sent: %d jobs", len(jobs))
    except Exception as exc:
        logger.error("Failed to send digest: %s", exc)
