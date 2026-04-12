import asyncio
import logging
import os

from telegram import Bot

logger = logging.getLogger(__name__)


def send_alert(title: str, company: str, location: str, url: str):
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

        async def _send():
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=text)

        asyncio.run(_send())
        logger.info("Alert sent: %s at %s", title, company)
    except Exception as exc:
        logger.error("Failed to send Telegram alert for %r: %s", title, exc)
