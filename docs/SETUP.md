# Setup Guide — clawpi-scout

Complete guide to setting up a Raspberry Pi as a scout node for [OpenClaw](https://openclaw.ai). Covers everything from unboxing to receiving your first Telegram alert.

---

## Prerequisites

| Item | Details |
|------|---------|
| Raspberry Pi | Pi 4 or Pi 5 (any RAM) |
| MicroSD card | 32 GB+ recommended |
| Power supply | USB-C, 5V/3A minimum |
| Ethernet or WiFi | For initial setup and ongoing connectivity |
| OpenClaw gateway | Running on another Pi or Mac ([clawpi-ai](https://github.com/BigDawg013/clawpi-ai)) |
| Telegram bot token | From [@BotFather](https://t.me/BotFather) |

---

## Phase 1 — Flash the OS

### 1.1 Download Raspberry Pi Imager

```bash
# macOS
brew install --cask raspberry-pi-imager

# Or download from https://www.raspberrypi.com/software/
```

### 1.2 Flash Raspberry Pi OS

1. Insert the MicroSD card into your computer
2. Open Raspberry Pi Imager
3. Choose OS: **Raspberry Pi OS Lite (64-bit)** — no desktop needed
4. Choose storage: select your MicroSD card
5. Click the **gear icon** for advanced options:
   - **Set hostname** (e.g. `clawpiscout`)
   - **Enable SSH**: Use password authentication
   - **Set username and password**
   - **Configure WiFi** (if not using ethernet)
   - **Set locale**: your timezone
6. Click **Write** and wait for it to finish

### 1.3 First boot

1. Insert the MicroSD card into the Pi
2. Connect ethernet (recommended) or rely on WiFi configured above
3. Connect power — the Pi boots automatically
4. Wait ~2 minutes for first boot to complete

---

## Phase 2 — Connect via SSH

### 2.1 Find the Pi

```bash
# Option A — mDNS (if your network supports it)
ping clawpiscout.local

# Option B — scan your network (macOS)
arp -a | grep -i "raspberry\|dc:a6\|e4:5f\|28:cd\|2c:cf\|d8:3a"

# Option C — check your router's admin page
```

### 2.2 SSH in

```bash
ssh <your-username>@<PI_IP_ADDRESS>
```

Accept the fingerprint on first connection.

### 2.3 Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Phase 3 — Install Tailscale

Tailscale creates an encrypted mesh network between the scout Pi and your OpenClaw gateway so they can reach each other from anywhere.

### 3.1 Install

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 3.2 Authenticate

```bash
sudo tailscale up
```

This prints a URL — open it in your browser and sign in with the same Tailscale account used on your gateway machine.

### 3.3 Verify

```bash
tailscale status
```

You should see both devices listed. Note the gateway's Tailscale IP (e.g. `100.x.x.x`).

### 3.4 Test connectivity

```bash
# Ping the gateway machine
ping -c 3 <GATEWAY_TAILSCALE_IP>

# Test the OpenClaw gateway directly
curl -s http://<GATEWAY_TAILSCALE_IP>:18789
```

---

## Phase 4 — Install the scout

### 4.1 Install system dependencies

```bash
sudo apt install -y git python3-pip python3-venv i2c-tools python3-lgpio
```

### 4.2 Enable I2C (for LCD display)

```bash
sudo raspi-config nonint do_i2c 0
sudo modprobe i2c-dev
```

### 4.3 Clone the repo

```bash
git clone https://github.com/BigDawg013/clawpi-scout.git ~/clawpi-scout
cd ~/clawpi-scout
```

### 4.4 Run the install script

```bash
bash scripts/install.sh
```

This creates a Python virtual environment, installs all dependencies, and sets up a systemd service.

### 4.5 Configure

```bash
cp config/scout.yaml.example config/scout.yaml
nano config/scout.yaml
```

Fill in:
- `gateway.url` — your gateway's Tailscale IP and port (e.g. `http://100.x.x.x:18789`)
- `telegram.bot_token` — from [@BotFather](https://t.me/BotFather)
- `telegram.chat_id` — your Telegram user ID (message [@userinfobot](https://t.me/userinfobot) to find it)

### 4.6 Start the scout

```bash
sudo systemctl start clawpi-scout
sudo systemctl status clawpi-scout
```

### 4.7 Check logs

```bash
journalctl -u clawpi-scout -f
```

You should see health checks running every 60 seconds.

---

## Phase 5 — Verify everything

### 5.1 Health check working

```bash
journalctl -u clawpi-scout --since "2 minutes ago" --no-pager
```

Look for `health check ok` lines.

### 5.2 Test the alert pipeline

Temporarily stop the OpenClaw gateway on the other machine:

```bash
# On the gateway machine (e.g. clawpi)
systemctl --user stop openclaw-gateway
```

Within 3 minutes the scout should send a Telegram alert: "ALERT: OpenClaw gateway unreachable — 3 consecutive failures."

Restart the gateway:

```bash
systemctl --user start openclaw-gateway
```

The scout should send a recovery message: "Gateway RECOVERED — back online."

### 5.3 Install morning briefing (optional)

```bash
bash scripts/install-cron.sh
```

This sends a daily Telegram summary at 8 AM with gateway status, CPU temp, disk, memory, and Tailscale connectivity.

---

## GPIO dashboard (optional)

If you have the hardware, see [docs/WIRING.md](WIRING.md) for complete wiring diagrams covering all 10 components.

To test the displays without wiring the full dashboard:

```bash
cd ~/clawpi-scout
python scripts/demo_displays.py
```

To disable displays you haven't wired yet, edit `config/scout.yaml`:

```yaml
gpio:
  bar_graph: false
  seven_segment: false
  dot_matrix: false
```

---

## Useful commands

| Command | What it does |
|---------|-------------|
| `sudo systemctl start clawpi-scout` | Start the scout |
| `sudo systemctl stop clawpi-scout` | Stop the scout |
| `sudo systemctl restart clawpi-scout` | Restart after config changes |
| `sudo systemctl status clawpi-scout` | Check if running |
| `journalctl -u clawpi-scout -f` | Follow live logs |
| `python -m scout.briefing` | Send briefing now |
| `python scripts/demo_displays.py` | Test GPIO displays |
| `tailscale status` | Check Tailscale connection |

---

## Troubleshooting

### Scout can't reach the gateway

```bash
tailscale status                              # Both devices listed?
tailscale ping <gateway-hostname>             # Direct connectivity?
curl http://<GATEWAY_TAILSCALE_IP>:18789      # Gateway responding?
```

### Scout won't start

```bash
journalctl -u clawpi-scout --no-pager -n 50  # Check error logs
cd ~/clawpi-scout && .venv/bin/python -m scout.main  # Run manually
```

### Telegram alerts not sending

```bash
# Test the bot token directly
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# Check for 401 errors in logs
journalctl -u clawpi-scout | grep "telegram"
```

### LCD not working

```bash
sudo i2cdetect -y 1                          # Should show address 0x27
ls /dev/i2c-*                                 # I2C device exists?
sudo raspi-config nonint do_i2c 0             # Enable I2C if missing
```

### Terminal issues over SSH

If you see `Error opening terminal: xterm-ghostty` or similar:

```bash
export TERM=xterm
```

Add to `~/.bashrc` to make it permanent.
