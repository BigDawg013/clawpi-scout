"""Stats pusher — sends dashboard data to Vercel API."""

import asyncio
import logging
import time

import aiohttp

from scout.briefing import get_system_stats

log = logging.getLogger("scout.stats_pusher")


class StatsPusher:
    def __init__(self, config: dict, health, dashboard, alerter):
        dash_cfg = config.get("dashboard", {})
        self.url = dash_cfg.get("url", "")
        self.api_key = dash_cfg.get("api_key", "")
        self.interval = dash_cfg.get("push_interval", 60)
        self.health = health
        self.dashboard = dashboard
        self.alerter = alerter

    @property
    def configured(self) -> bool:
        return bool(self.url and self.api_key)

    def _collect_payload(self) -> dict:
        # System stats
        try:
            system = get_system_stats()
        except Exception as e:
            log.warning("failed to collect system stats: %s", e)
            system = {}

        # Sensor readings
        temp, humidity = self.dashboard.read_dht11()

        # LED state
        if self.dashboard._last_gateway_ok:
            led_state = "green"
        elif hasattr(self.health, '_alerted') and self.health._alerted:
            led_state = "red"
        else:
            led_state = "yellow"

        # Matrix pattern
        matrix_pattern = "smiley" if self.dashboard._last_gateway_ok else "x"

        # Recent alerts from TelegramAlerter
        alerts = []
        for a in self.alerter._recent_alerts:
            alerts.append({
                "ts": a["ts"],
                "message": a["message"],
            })

        return {
            "ts": int(time.time()),
            "gateway": {
                "status": self.health.status,
                "consecutive_ok": self.health.consecutive_ok,
                "uptime_seconds": self.health.uptime_seconds,
            },
            "system": {
                "cpu_temp": system.get("cpu_temp", 0),
                "disk_used_pct": system.get("disk_used_pct", 0),
                "mem_total_mb": system.get("mem_total_mb", 0),
                "mem_available_mb": system.get("mem_available_mb", 0),
                "load_avg": system.get("load_avg", "0"),
            },
            "sensor": {
                "temperature": temp,
                "humidity": humidity,
            },
            "dashboard": {
                "health_score": self.dashboard._health_score,
                "led_state": led_state,
                "matrix_pattern": matrix_pattern,
            },
            "alerts": alerts,
        }

    async def _push(self, payload: dict) -> bool:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        log.debug("stats pushed successfully")
                        return True
                    else:
                        body = await resp.text()
                        log.warning("stats push failed (%d): %s", resp.status, body[:100])
                        return False
        except Exception as e:
            log.warning("stats push error: %s", e)
            return False

    async def run(self, stop: asyncio.Event):
        if not self.configured:
            log.info("stats pusher not configured — skipping")
            await stop.wait()
            return

        log.info("stats pusher started — pushing to %s every %ds", self.url, self.interval)

        # Wait a bit for initial health check to complete
        try:
            await asyncio.wait_for(stop.wait(), timeout=10)
            return
        except asyncio.TimeoutError:
            pass

        while not stop.is_set():
            payload = self._collect_payload()
            await self._push(payload)

            try:
                await asyncio.wait_for(stop.wait(), timeout=self.interval)
                break
            except asyncio.TimeoutError:
                pass

        log.info("stats pusher stopped")
