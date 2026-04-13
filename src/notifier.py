import asyncio
import logging
import os
from datetime import datetime

from telegram import Bot

logger = logging.getLogger(__name__)


def send_alert(title: str, company: str, location: str, url: str, source: str = ""):
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
