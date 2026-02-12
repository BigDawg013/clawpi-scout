"""Health monitor — checks OpenClaw gateway availability."""

import asyncio
import logging
import time

import aiohttp

log = logging.getLogger("scout.health")


class HealthMonitor:
    def __init__(self, config: dict, alerter, dashboard=None):
        self.url = config.get("url", "")
        self.interval = config.get("health_interval", 60)
        self.timeout = config.get("timeout", 10)
        self.max_failures = config.get("max_failures", 3)
        self.alerter = alerter
        self.dashboard = dashboard

        self._consecutive_failures = 0
        self._consecutive_ok = 0
        self._alerted = False
        self._last_ok = None
        self._start_time = time.time()

    @property
    def status(self) -> str:
        return "down" if self._alerted else "up"

    @property
    def consecutive_ok(self) -> int:
        return self._consecutive_ok

    @property
    def uptime_seconds(self) -> int:
        return self._uptime_seconds()

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

    def _uptime_str(self) -> str:
        elapsed = int(time.time() - self._start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"Up {hours}h{minutes:02d}m"

    def _uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)

    async def run(self, stop: asyncio.Event):
        log.info("health monitor started — checking %s every %ds", self.url, self.interval)
        while not stop.is_set():
            # Yellow LED while checking
            if self.dashboard:
                self.dashboard.led_checking()

            ok = await self.check()

            if ok:
                if self._alerted:
                    log.info("gateway recovered")
                    await self.alerter.send("Gateway RECOVERED — back online.")
                    self._alerted = False
                self._consecutive_failures = 0
                self._consecutive_ok += 1
                log.debug("gateway ok")

                # Green LED + update LCD
                if self.dashboard:
                    self.dashboard.led_ok()
                    self.dashboard.update_lcd(True, self._uptime_str())
                    self.dashboard.on_health_check(
                        True, self._consecutive_ok, self._uptime_seconds()
                    )
            else:
                self._consecutive_failures += 1
                self._consecutive_ok = 0
                log.warning(
                    "gateway unreachable (%d/%d)",
                    self._consecutive_failures,
                    self.max_failures,
                )

                # Red LED
                if self.dashboard:
                    self.dashboard.led_fail()
                    self.dashboard.update_lcd(False, self._uptime_str())
                    self.dashboard.on_health_check(
                        False, 0, self._uptime_seconds()
                    )

                if self._consecutive_failures >= self.max_failures and not self._alerted:
                    await self.alerter.send(
                        f"ALERT: OpenClaw gateway unreachable — "
                        f"{self._consecutive_failures} consecutive failures. "
                        f"Last OK: {self._format_last_ok()}"
                    )
                    self._alerted = True
                    # Buzzer alarm
                    if self.dashboard:
                        await self.dashboard.alarm(pulses=3)
                        self.dashboard.update_lcd(False, self._uptime_str())

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
