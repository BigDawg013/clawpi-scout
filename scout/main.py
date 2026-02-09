"""Entry point for clawpi-scout daemon."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import yaml

from scout.health.monitor import HealthMonitor
from scout.watchers.watcher import WatcherManager
from scout.alerts.telegram import TelegramAlerter

CONFIG_PATH = Path(__file__).parent.parent / "config" / "scout.yaml"

log = logging.getLogger("scout")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def setup_logging(config: dict):
    level = getattr(logging, config.get("logging", {}).get("level", "INFO"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run():
    config = load_config()
    setup_logging(config)

    log.info("clawpi-scout starting")

    alerter = TelegramAlerter(config.get("telegram", {}))
    health = HealthMonitor(config.get("gateway", {}), alerter)
    watchers = WatcherManager(config.get("watchers", {}), alerter)

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    tasks = [
        asyncio.create_task(health.run(stop)),
        asyncio.create_task(watchers.run(stop)),
    ]

    log.info("all scouts active — monitoring")
    await stop.wait()
    log.info("shutdown signal received")

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("clawpi-scout stopped")


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
