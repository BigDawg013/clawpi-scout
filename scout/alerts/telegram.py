"""Telegram alerter — sends messages directly via Telegram Bot API."""

import logging
import time

import aiohttp

log = logging.getLogger("scout.alerts")


class TelegramAlerter:
    def __init__(self, config: dict):
        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
        self.cooldown = config.get("alert_cooldown", 300)
        self._last_sent: dict[str, float] = {}
        self._recent_alerts: list[dict] = []  # last 10 alerts for dashboard

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(self, message: str, key: str | None = None):
        if not self.configured:
            log.warning("telegram not configured — alert dropped: %s", message)
            return

        now = time.time()
        cooldown_key = key or message[:50]
        last = self._last_sent.get(cooldown_key, 0)
        if now - last < self.cooldown:
            log.debug("alert suppressed (cooldown): %s", cooldown_key)
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"🔍 clawpi-scout\n\n{message}",
            "parse_mode": "HTML",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        log.info("telegram alert sent: %s", message[:80])
                        self._last_sent[cooldown_key] = now
                        self._recent_alerts.append({"ts": now, "message": message})
                        self._recent_alerts = self._recent_alerts[-10:]
                    else:
                        body = await resp.text()
                        log.error("telegram send failed (%d): %s", resp.status, body)
        except Exception as e:
            log.error("telegram send error: %s", e)
