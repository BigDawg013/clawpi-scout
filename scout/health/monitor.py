"""Health monitor — checks OpenClaw gateway availability."""

import asyncio
import logging
import time

import aiohttp

log = logging.getLogger("scout.health")


class HealthMonitor:
    def __init__(self, config: dict, alerter):
        self.url = config.get("url", "https://bigs-mac-mini.tail7b895b.ts.net")
        self.interval = config.get("health_interval", 60)
        self.timeout = config.get("timeout", 10)
        self.max_failures = config.get("max_failures", 3)
        self.alerter = alerter

        self._consecutive_failures = 0
        self._alerted = False
        self._last_ok = None

    async def check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    ok = resp.status < 500
                    if ok:
                        self._last_ok = time.time()
                    return ok
        except Exception as e:
            log.warning("health check failed: %s", e)
            return False

    async def run(self, stop: asyncio.Event):
        log.info("health monitor started — checking %s every %ds", self.url, self.interval)
        while not stop.is_set():
            ok = await self.check()

            if ok:
                if self._alerted:
                    log.info("gateway recovered")
                    await self.alerter.send("Gateway RECOVERED — back online.")
                    self._alerted = False
                self._consecutive_failures = 0
                log.debug("gateway ok")
            else:
                self._consecutive_failures += 1
                log.warning(
                    "gateway unreachable (%d/%d)",
                    self._consecutive_failures,
                    self.max_failures,
                )
                if self._consecutive_failures >= self.max_failures and not self._alerted:
                    await self.alerter.send(
                        f"ALERT: OpenClaw gateway unreachable — "
                        f"{self._consecutive_failures} consecutive failures. "
                        f"Last OK: {self._format_last_ok()}"
                    )
                    self._alerted = True

            try:
                await asyncio.wait_for(stop.wait(), timeout=self.interval)
                break
            except asyncio.TimeoutError:
                pass

    def _format_last_ok(self) -> str:
        if self._last_ok is None:
            return "never"
        ago = int(time.time() - self._last_ok)
        if ago < 60:
            return f"{ago}s ago"
        return f"{ago // 60}m ago"
