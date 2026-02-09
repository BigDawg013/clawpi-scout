# clawpi-scout

Raspberry Pi scout node for [OpenClaw](https://github.com/BigDawg013/openclaw-setup) — health monitoring, web watchers, and Telegram alerting for a multi-agent AI system.

## What is this?

A lightweight always-on daemon running on a Raspberry Pi that acts as a **scout** for the main OpenClaw system on a Mac Mini. The scout observes, detects, and reports — it doesn't think.

| Capability | What it does |
|-----------|-------------|
| **Health monitor** | Pings the OpenClaw gateway every 60s, alerts on failure |
| **Web watchers** | Monitors URLs/APIs for changes, only reports when something matters |
| **Telegram alerts** | Independent alerting that works even when OpenClaw is offline |
| **Morning briefing** | Daily summary — gateway status, system health, Pi vitals |

## Architecture

```
┌──────────────────────────────────────────┐
│  Mac Mini · bigs-mac-mini                │
│  ┌────────────────────────────────────┐  │
│  │ OpenClaw Gateway                   │  │
│  │ ws://127.0.0.1:18789              │  │
│  │                                    │  │
│  │ 🦞 BigDawg · Haiku 4.5  (router)  │  │
│  │ 💻 Coder   · Opus 4.5   (engineer)│  │
│  │ 🧠 Brain   · Opus 4.6   (strategy)│  │
│  └────────────────────────────────────┘  │
│                    │                      │
│  Tailscale Serve   │                      │
│  https://bigs-mac-mini.tail*.ts.net      │
└────────────────────┬─────────────────────┘
                     │ Tailscale (encrypted)
┌────────────────────┴─────────────────────┐
│  Raspberry Pi · clawpi                    │
│  100.107.226.78                           │
│  ┌────────────────────────────────────┐  │
│  │ clawpi-scout daemon                │  │
│  │                                    │  │
│  │ 🔍 Health monitor    (every 60s)   │  │
│  │ 👁️ Web watchers      (every 5min)  │  │
│  │ 📋 Morning briefing  (daily 8AM)   │  │
│  │ 🔔 Telegram alerts   (on events)   │  │
│  └────────────────────────────────────┘  │
│                    │                      │
│            @clawpi_scout_bot              │
│               (Telegram)                  │
└──────────────────────────────────────────┘
```

## Project structure

```
clawpi-scout/
├── README.md                   # You are here
├── requirements.txt            # Python dependencies
├── config/
│   ├── scout.yaml.example      # Config template (committed)
│   └── scout.yaml              # Your config with secrets (gitignored)
├── scout/
│   ├── __init__.py
│   ├── main.py                 # Entry point — runs health + watchers
│   ├── briefing.py             # Morning briefing — daily Telegram summary
│   ├── health/
│   │   ├── __init__.py
│   │   └── monitor.py          # Gateway health checks
│   ├── watchers/
│   │   ├── __init__.py
│   │   └── watcher.py          # URL/API change detection
│   └── alerts/
│       ├── __init__.py
│       └── telegram.py         # Direct Telegram Bot API alerting
├── scripts/
│   ├── install.sh              # One-command setup (venv + systemd)
│   └── install-cron.sh         # Cron jobs (morning briefing)
└── docs/
    └── SETUP.md                # Full A-to-Z guide
```

## Quick start

```bash
# On the Raspberry Pi
git clone https://github.com/BigDawg013/clawpi-scout.git
cd clawpi-scout

# Install daemon + systemd service
bash scripts/install.sh

# Configure
cp config/scout.yaml.example config/scout.yaml
nano config/scout.yaml          # Add your tokens, targets

# Start
sudo systemctl start clawpi-scout

# Install morning briefing cron
bash scripts/install-cron.sh
```

## Configuration

All config lives in `config/scout.yaml` (gitignored — secrets stay on the Pi).

| Section | Key fields | Description |
|---------|-----------|-------------|
| `gateway` | `url`, `health_interval`, `max_failures` | What to monitor, how often, when to alert |
| `telegram` | `bot_token`, `chat_id` | Where alerts are sent |
| `watchers` | `targets[]` | URLs/APIs to watch for changes |
| `logging` | `level` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

See [`config/scout.yaml.example`](config/scout.yaml.example) for full documentation.

## How it works

### Health monitor

Runs continuously as a systemd service. Every 60 seconds:
1. HTTP GET to the OpenClaw gateway via Tailscale Serve
2. If 3 consecutive checks fail → Telegram alert
3. When gateway recovers → Telegram recovery message
4. Cooldown prevents alert spam (5 min between repeats)

### Web watchers

Monitors configured URLs every 5 minutes:
1. Fetches each target URL
2. SHA-256 hashes the response body
3. Compares against previous hash
4. If changed → Telegram notification with old/new hash
5. First run establishes baseline (no alert)

### Morning briefing

Cron job at 8:00 AM daily. Sends a Telegram summary:
- Gateway status (online/offline)
- Pi system vitals (CPU temp, disk, memory, load)
- Tailscale connectivity
- Watcher target count

### Telegram alerts

Independent from OpenClaw — uses the Telegram Bot API directly from the Pi. Works even when the Mac Mini is completely down.

## Operations

| Command | Description |
|---------|-------------|
| `sudo systemctl start clawpi-scout` | Start the daemon |
| `sudo systemctl stop clawpi-scout` | Stop the daemon |
| `sudo systemctl restart clawpi-scout` | Restart after config changes |
| `sudo systemctl status clawpi-scout` | Check if running |
| `journalctl -u clawpi-scout -f` | Follow live logs |
| `python -m scout.briefing` | Send briefing now |
| `tailscale status` | Check Tailscale connection |

## Full setup guide

See [docs/SETUP.md](docs/SETUP.md) for the complete A-to-Z guide — from flashing the SD card to a running scout.

## Related

- [openclaw-setup](https://github.com/BigDawg013/openclaw-setup) — The multi-agent AI system this scout monitors
- [OpenClaw](https://openclaw.ai) — The platform powering the agents
