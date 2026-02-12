<p align="center">
  <img src="https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white" alt="Raspberry Pi" />
  <img src="https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/network-Tailscale-0052ff?style=flat-square&logo=tailscale&logoColor=white" alt="Tailscale" />
  <img src="https://img.shields.io/badge/alerts-Telegram-26a5e4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License" />
</p>

# clawpi-scout

A Raspberry Pi watchdog daemon that monitors an [OpenClaw](https://openclaw.ai) AI gateway and reports status through **Telegram alerts** and a **physical GPIO dashboard** with LEDs, LCD, sensors, and multiplexed displays.

> The scout observes, detects, and reports — it doesn't think.

---

## What it does

| Module | Function | Frequency |
|--------|----------|-----------|
| **Health monitor** | Pings the OpenClaw gateway, alerts after 3 consecutive failures | Every 60s |
| **Web watchers** | Monitors URLs/APIs, alerts when content changes | Every 5 min |
| **Morning briefing** | Telegram summary — gateway status, CPU temp, disk, memory | Daily 8 AM |
| **GPIO dashboard** | Physical LED/LCD/sensor display showing live system state | Real-time |

---

## GPIO Dashboard

The scout drives a physical breadboard dashboard with **10 components** across **17 GPIO pins**:

| Component | What it shows | Drive method |
|-----------|--------------|-------------|
| 3x Status LEDs | Green=OK, Yellow=checking, Red=down | Direct GPIO |
| Active buzzer | Alarm on 3 consecutive failures | Direct GPIO |
| Push button | Press to send instant briefing to Telegram | Direct GPIO |
| DHT11 sensor | Temperature + humidity on LCD | Direct GPIO |
| LCD1602 (I2C) | Gateway status, uptime, temp readout | I2C bus |
| **LED bar graph** (10-seg) | Health gauge: fills with consecutive successes | Direct GPIO (10 pins) |
| **4-digit 7-segment** | Uptime counter in HH:MM with blinking colon | 1x 74HC595 shift register |
| **8x8 dot matrix** | Smiley when UP, X when DOWN, blinks on alarm | 2x 74HC595 daisy-chained |

All three shift registers share 3 GPIO pins (data, latch, clock) via daisy-chaining. A background thread multiplexes the 7-segment digits and matrix rows at ~1kHz for flicker-free display.

See [docs/WIRING.md](docs/WIRING.md) for complete wiring diagrams and breadboard layout.

---

## Architecture

```
                    Tailscale mesh (encrypted)
                             |
         +-------------------+-------------------+
         |                                       |
+--------+----------+               +-----------+-----------+
|  OpenClaw Gateway  |               |   clawpi-scout        |
|  (Pi or Mac Mini)  |  <-- ping --- |   Raspberry Pi        |
|  port 18789        |               |                       |
+--------------------+               |   Health monitor      |
                                     |   Web watchers        |
                                     |   Morning briefing    |
                                     |   GPIO dashboard      |
                                     |        |              |
                                     +--------+--------------+
                                              |
                                     +--------+--------+
                                     |    Telegram     |
                                     |   @your_bot    |
                                     +-----------------+
```

---

## Quick start

```bash
# Clone on the Pi
git clone https://github.com/BigDawg013/clawpi-scout.git ~/clawpi-scout
cd ~/clawpi-scout

# Install (creates venv + systemd service)
bash scripts/install.sh

# Configure
cp config/scout.yaml.example config/scout.yaml
nano config/scout.yaml   # Add gateway URL, Telegram bot token, chat ID

# Start
sudo systemctl start clawpi-scout

# Install morning briefing cron (optional)
bash scripts/install-cron.sh
```

See [docs/SETUP.md](docs/SETUP.md) for the full A-to-Z guide — from flashing the SD card to receiving your first alert.

---

## Project structure

```
clawpi-scout/
├── config/
│   ├── scout.yaml.example        # Config template (committed, no secrets)
│   └── scout.yaml                # Your config with secrets (gitignored)
├── docs/
│   ├── SETUP.md                  # Full setup guide
│   └── WIRING.md                 # GPIO wiring diagrams + breadboard layout
├── scout/
│   ├── main.py                   # Entry point — async daemon
│   ├── briefing.py               # Morning briefing generator
│   ├── health/
│   │   └── monitor.py            # Gateway health checks (async)
│   ├── watchers/
│   │   └── watcher.py            # URL/API change detection (async)
│   ├── alerts/
│   │   └── telegram.py           # Telegram Bot API alerting
│   └── gpio/
│       ├── dashboard.py          # Main GPIO coordinator
│       ├── bar_graph.py          # 10-segment LED bar graph driver
│       ├── seven_segment.py      # 4-digit 7-segment display driver
│       ├── dot_matrix.py         # 8x8 matrix pattern definitions
│       ├── shift_register.py     # 74HC595 bit-bang driver
│       └── multiplex_thread.py   # Background thread (~1kHz refresh)
├── scripts/
│   ├── install.sh                # One-command setup (venv + systemd)
│   ├── install-cron.sh           # Cron job for morning briefing
│   └── demo_displays.py         # Test all GPIO displays
└── requirements.txt
```

---

## Configuration

All config lives in `config/scout.yaml` (gitignored — secrets stay on the Pi).

```yaml
gateway:
  url: "http://<TAILSCALE_IP>:18789"   # OpenClaw gateway address
  health_interval: 60                   # Seconds between health checks
  timeout: 10                           # Seconds before check is "failed"
  max_failures: 3                       # Consecutive failures before alert

telegram:
  bot_token: ""                         # From @BotFather
  chat_id: ""                           # Your Telegram user/group ID

gpio:
  bar_graph: true                       # Enable LED bar graph
  seven_segment: true                   # Enable 7-segment display
  dot_matrix: true                      # Enable dot matrix display
```

See [`config/scout.yaml.example`](config/scout.yaml.example) for full documentation with all options.

---

## How it works

**Health monitor** — Runs as a systemd service. Every 60 seconds it pings the OpenClaw gateway over Tailscale. After 3 consecutive failures it fires a Telegram alert and triggers the buzzer alarm. On recovery it sends an all-clear message.

**Web watchers** — Monitors configured URLs every 5 minutes. SHA-256 hashes each response. On change, sends a Telegram notification. First run establishes a baseline silently.

**Morning briefing** — Cron job at 8 AM. Sends a Telegram summary with gateway status, CPU temperature, disk/memory usage, Tailscale connectivity, and watcher count.

**GPIO dashboard** — The physical display updates in real time. LEDs show instant status. The bar graph tracks a rolling health score (0-10). The 7-segment shows uptime in HH:MM. The dot matrix shows a smiley face when healthy, an X when down, and blinks during alarms.

---

## Operations

```bash
sudo systemctl start clawpi-scout       # Start
sudo systemctl stop clawpi-scout        # Stop
sudo systemctl restart clawpi-scout     # Restart (after config changes)
sudo systemctl status clawpi-scout      # Check status
journalctl -u clawpi-scout -f           # Follow live logs
python -m scout.briefing                # Send briefing now
python scripts/demo_displays.py         # Test all GPIO displays
tailscale status                        # Check Tailscale connection
```

---

## Hardware

**Required:**
- Raspberry Pi 4 or 5 (any RAM)
- MicroSD card (32 GB+)
- Internet connection (Ethernet or WiFi)

**For the GPIO dashboard (optional):**
- 830-hole breadboard + GPIO T-cobbler
- 3x LEDs (green, red, yellow) + 220 ohm resistors
- Active buzzer, push button
- DHT11 temperature/humidity sensor
- LCD1602 with I2C backpack (address 0x27)
- 10-segment LED bar graph + 10x 220 ohm resistors
- 3x 74HC595 shift registers (daisy-chained)
- 4-digit common-cathode 7-segment display
- 8x8 LED dot matrix
- Jumper wires (M-M, M-F)

All components come from the [Freenove FNK0020 kit](https://github.com/Freenove/Freenove_Ultimate_Starter_Kit_for_Raspberry_Pi).

---

## Related

- **[clawpi-ai](https://github.com/BigDawg013/clawpi-ai)** — OpenClaw on a Raspberry Pi (the gateway this scout monitors)
- **[OpenClaw](https://openclaw.ai)** — The multi-agent AI platform

---

## License

[MIT](LICENSE)
