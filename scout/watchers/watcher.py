"""Web watcher — monitors URLs for changes."""

import asyncio
import hashlib
import logging

import aiohttp

log = logging.getLogger("scout.watchers")


class WatcherManager:
    def __init__(self, config: dict, alerter):
        self.interval = config.get("check_interval", 300)
        self.targets = config.get("targets", [])
        self.alerter = alerter
        self._state: dict[str, str] = {}

    async def check_target(self, target: dict) -> bool:
        name = target["name"]
        url = target["url"]
        notify_on = target.get("notify_on", "change")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    body = await resp.text()
                    current_hash = hashlib.sha256(body.encode()).hexdigest()[:16]

                    prev_hash = self._state.get(name)
                    self._state[name] = current_hash

                    if prev_hash is None:
                        log.info("watcher [%s] baseline: %s", name, current_hash)
                        return False

                    if current_hash != prev_hash:
                        log.info("watcher [%s] changed: %s → %s", name, prev_hash, current_hash)
                        if notify_on in ("change", "always"):
                            await self.alerter.send(
                                f"Watcher <b>{name}</b> detected a change.\n"
                                f"URL: {url}\n"
                                f"Hash: {prev_hash} → {current_hash}",
                                key=f"watcher:{name}",
                            )
                        return True

                    log.debug("watcher [%s] unchanged", name)
                    if notify_on == "always":
                        await self.alerter.send(
                            f"Watcher <b>{name}</b> checked — no change.",
                            key=f"watcher:{name}",
                        )
                    return False

        except Exception as e:
            log.warning("watcher [%s] error: %s", name, e)
            if notify_on in ("error", "always"):
                await self.alerter.send(
                    f"Watcher <b>{name}</b> error: {e}",
                    key=f"watcher:{name}:error",
                )
            return False

    async def run(self, stop: asyncio.Event):
        if not self.targets:
            log.info("no watcher targets configured — watcher idle")
            await stop.wait()
            return

        log.info("watcher started — %d targets, checking every %ds", len(self.targets), self.interval)
        while not stop.is_set():
            for target in self.targets:
                await self.check_target(target)

            try:
                await asyncio.wait_for(stop.wait(), timeout=self.interval)
                break
            except asyncio.TimeoutError:
                pass
