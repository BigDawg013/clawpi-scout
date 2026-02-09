"""Morning briefing — sends a daily status summary to Telegram."""

import asyncio
import logging
import platform
import shutil
import time

import aiohttp
import yaml

from scout.alerts.telegram import TelegramAlerter

CONFIG_PATH = __file__.replace("briefing.py", "../config/scout.yaml")

log = logging.getLogger("scout.briefing")


async def get_gateway_status(url: str, timeout: int = 10) -> tuple[bool, int]:
    """Check gateway and return (ok, status_code)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                return resp.status < 500, resp.status
    except Exception:
        return False, 0


async def get_tailscale_ip() -> str:
    """Get this device's Tailscale IP."""
    proc = await asyncio.create_subprocess_exec(
        "tailscale", "ip", "-4",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() if proc.returncode == 0 else "unknown"


def get_system_stats() -> dict:
    """Collect basic system stats."""
    disk = shutil.disk_usage("/")
    with open("/proc/meminfo") as f:
        mem = {}
        for line in f:
            parts = line.split()
            if parts[0] in ("MemTotal:", "MemAvailable:"):
                mem[parts[0].rstrip(":")] = int(parts[1]) // 1024  # MB

    with open("/proc/loadavg") as f:
        load = f.read().split()[:3]

    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        temp = int(f.read().strip()) / 1000

    return {
        "disk_used_pct": round(disk.used / disk.total * 100, 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "mem_total_mb": mem.get("MemTotal", 0),
        "mem_available_mb": mem.get("MemAvailable", 0),
        "load_avg": " / ".join(load),
        "cpu_temp": temp,
        "hostname": platform.node(),
    }


async def run_briefing():
    """Generate and send the morning briefing."""
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "config" / "scout.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    alerter = TelegramAlerter(config.get("telegram", {}))
    if not alerter.configured:
        print("Telegram not configured — cannot send briefing")
        return

    gw_url = config.get("gateway", {}).get("url", "")
    gw_ok, gw_status = await get_gateway_status(gw_url)
    ts_ip = await get_tailscale_ip()
    stats = get_system_stats()

    gw_icon = "✅" if gw_ok else "🔴"
    temp_icon = "🟢" if stats["cpu_temp"] < 60 else "🟡" if stats["cpu_temp"] < 75 else "🔴"

    msg = (
        f"📋 <b>Morning Briefing — {stats['hostname']}</b>\n"
        f"\n"
        f"<b>Gateway</b>\n"
        f"  {gw_icon} Status: {'Online' if gw_ok else 'OFFLINE'} ({gw_status})\n"
        f"  🔗 {gw_url}\n"
        f"\n"
        f"<b>System</b>\n"
        f"  {temp_icon} CPU temp: {stats['cpu_temp']}°C\n"
        f"  💾 Disk: {stats['disk_used_pct']}% used ({stats['disk_free_gb']} GB free)\n"
        f"  🧠 Memory: {stats['mem_available_mb']} MB free / {stats['mem_total_mb']} MB\n"
        f"  📊 Load: {stats['load_avg']}\n"
        f"\n"
        f"<b>Network</b>\n"
        f"  🌐 Tailscale: {ts_ip}\n"
        f"\n"
        f"<b>Watchers</b>\n"
        f"  👁️ {len(config.get('watchers', {}).get('targets', []))} targets configured\n"
    )

    await alerter.send(msg, key="briefing")
    print("Briefing sent")


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_briefing())


if __name__ == "__main__":
    main()
