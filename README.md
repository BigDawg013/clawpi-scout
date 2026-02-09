# clawpi-scout

Raspberry Pi scout node for [OpenClaw](https://github.com/BigDawg013/openclaw-setup) — health monitoring, web watchers, and Telegram alerting for a multi-agent AI system.

## What is this?

A lightweight always-on daemon running on a Raspberry Pi that acts as a **scout** for the main OpenClaw system on a Mac Mini. The scout observes, detects, and reports — it doesn't think.

**The scout does three things:**
1. **Health monitoring** — pings the OpenClaw gateway and alerts you if it goes down
2. **Web watchers** — monitors URLs/APIs for changes, only reports when something matters
3. **Telegram alerts** — independent alerting that works even when OpenClaw is offline

## Architecture

```
┌──────────────────────────────┐
│  Mac Mini (100.75.53.90)     │
│  ┌────────────────────────┐  │
│  │ OpenClaw Gateway       │  │
│  │ ws://127.0.0.1:18789   │  │
│  │                        │  │
│  │ 🦞 BigDawg (Haiku 4.5) │  │
│  │ 💻 Coder   (Opus 4.5)  │  │
│  │ 🧠 Brain   (Opus 4.6)  │  │
│  └────────────────────────┘  │
└──────────┬───────────────────┘
           │ Tailscale
           │ (100.x.x.x)
┌──────────┴───────────────────┐
│  Raspberry Pi (clawpi)       │
│  100.107.226.78              │
│  ┌────────────────────────┐  │
│  │ clawpi-scout           │  │
│  │                        │  │
│  │ 🔍 Health monitor      │  │
│  │ 👁️ Web watchers        │  │
│  │ 🔔 Telegram alerts     │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

## Project structure

```
clawpi-scout/
├── README.md              # You are here
├── config/
│   └── scout.yaml         # All configuration (targets, intervals, tokens)
├── scout/
│   ├── __init__.py
│   ├── main.py            # Entry point — runs all scouts
│   ├── health/
│   │   ├── __init__.py
│   │   └── monitor.py     # Gateway & agent health checks
│   ├── watchers/
│   │   ├── __init__.py
│   │   └── watcher.py     # URL/API change detection
│   └── alerts/
│       ├── __init__.py
│       └── telegram.py    # Direct Telegram alerting
├── scripts/
│   └── install.sh         # One-command setup script
├── docs/
│   └── SETUP.md           # Full A-to-Z setup guide
└── requirements.txt
```

## Quick start

```bash
# On the Raspberry Pi
git clone https://github.com/BigDawg013/clawpi-scout.git
cd clawpi-scout
bash scripts/install.sh
# Edit config/scout.yaml with your tokens and targets
sudo systemctl start clawpi-scout
```

## Full setup guide

See [docs/SETUP.md](docs/SETUP.md) for the complete A-to-Z guide — from flashing the SD card to running the scout.

## Related

- [openclaw-setup](https://github.com/BigDawg013/openclaw-setup) — The main multi-agent system this scout monitors
