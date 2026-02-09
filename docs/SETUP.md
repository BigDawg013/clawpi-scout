# Setup Guide — A to Z

Complete guide to setting up a Raspberry Pi as a scout node for OpenClaw. Covers everything from unboxing to a running scout daemon.

---

## Prerequisites

| Item | Details |
|------|---------|
| Raspberry Pi | Pi 4 or Pi 5 (any RAM) |
| MicroSD card | 32GB+ recommended |
| Power supply | USB-C, 5V/3A minimum |
| Ethernet or Wi-Fi | For initial setup and ongoing connectivity |
| Mac Mini | Running OpenClaw with the gateway active |

---

## Phase 1 — Flash the OS

### 1.1 Download Raspberry Pi Imager

On your main computer:

```bash
# macOS
brew install --cask raspberry-pi-imager

# Or download from https://www.raspberrypi.com/software/
```

### 1.2 Flash Raspberry Pi OS

1. Insert the MicroSD card into your computer
2. Open Raspberry Pi Imager
3. Choose OS → **Raspberry Pi OS (64-bit)** — Debian Bookworm/Trixie
4. Choose storage → select your MicroSD card
5. Click the **gear icon** for advanced options:
   - **Set hostname**: `<pi-hostname>`
   - **Enable SSH**: Use password authentication
   - **Set username**: `<your-username>` (or your preferred username)
   - **Set password**: choose a strong password
   - **Configure Wi-Fi**: enter your SSID and password (if not using ethernet)
   - **Set locale**: your timezone
6. Click **Write** and wait for it to finish

### 1.3 First boot

1. Insert the MicroSD card into the Pi
2. Connect ethernet (recommended) or rely on Wi-Fi configured above
3. Connect power — the Pi will boot automatically
4. Wait ~2 minutes for first boot to complete

---

## Phase 2 — Connect via SSH

### 2.1 Find the Pi on your network

From your main computer:

```bash
# Option A — if mDNS works on your network
ping <pi-hostname>.local

# Option B — scan the network (macOS)
arp -a | grep -i "raspberry\|dc:a6\|e4:5f\|28:cd\|2c:cf\|d8:3a"

# Option C — use your router's admin page to find the IP
```

### 2.2 SSH in

```bash
ssh <your-username>@<PI_IP_ADDRESS>
# Example: ssh <your-username>@<PI_LOCAL_IP>
```

Accept the fingerprint on first connection. You should see:

```
Linux <pi-hostname> 6.12.x+rpt-rpi-v8 #1 SMP PREEMPT Debian ... aarch64
<your-username>@<pi-hostname>:~$
```

### 2.3 Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Phase 3 — Install Tailscale

Tailscale creates a private network (tailnet) between the Pi and Mac Mini so they can reach each other from anywhere.

### 3.1 Install

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 3.2 Authenticate

```bash
sudo tailscale up
```

This will print a URL — open it in your browser and sign in with the same account used on your Mac Mini.

### 3.3 Verify connection

```bash
tailscale status
```

You should see both devices:

```
100.x.x.x  <pi-hostname>         you@  linux  -
100.x.x.x  <mac-mini-hostname>  you@  macOS  idle
```

### 3.4 Test connectivity

```bash
# Ping the Mac Mini over Tailscale
ping -c 3 <MAC_MINI_TAILSCALE_IP>
```

You can now SSH over Tailscale from anywhere:

```bash
ssh <your-username>@<CLAWPI_TAILSCALE_IP>
```

---

## Phase 4 — Install the Scout

### 4.1 Clone the repo

```bash
cd ~
git clone https://github.com/<your-username>/<pi-hostname>-scout.git
cd <pi-hostname>-scout
```

### 4.2 Run the install script

```bash
bash scripts/install.sh
```

This will:
- Create a Python virtual environment
- Install dependencies
- Copy the systemd service file
- Enable the service to start on boot

### 4.3 Configure

```bash
nano config/scout.yaml
```

Fill in:
- **gateway_url**: `ws://<MAC_MINI_TAILSCALE_IP>:18789` (your Mac Mini's Tailscale IP)
- **telegram_bot_token**: your Telegram bot token
- **telegram_chat_id**: your Telegram chat ID
- **watch_urls**: URLs you want to monitor

### 4.4 Start the scout

```bash
sudo systemctl start <pi-hostname>-scout
sudo systemctl status <pi-hostname>-scout
```

### 4.5 Check logs

```bash
journalctl -u <pi-hostname>-scout -f
```

---

## Phase 5 — Verify everything works

### 5.1 Health check

The scout should immediately start pinging the gateway. Check logs:

```bash
journalctl -u <pi-hostname>-scout --since "1 minute ago"
```

### 5.2 Test Telegram alert

Temporarily stop the OpenClaw gateway on your Mac Mini and verify the Pi sends a Telegram alert within 60 seconds.

### 5.3 Test web watcher

Add a test URL to `config/scout.yaml` and verify the scout detects changes.

---

## Useful commands

| Command | What it does |
|---------|-------------|
| `sudo systemctl start <pi-hostname>-scout` | Start the scout |
| `sudo systemctl stop <pi-hostname>-scout` | Stop the scout |
| `sudo systemctl restart <pi-hostname>-scout` | Restart after config changes |
| `sudo systemctl status <pi-hostname>-scout` | Check if running |
| `journalctl -u <pi-hostname>-scout -f` | Follow live logs |
| `tailscale status` | Check Tailscale connection |
| `tailscale ping <mac-mini-hostname>` | Ping Mac Mini via Tailscale |

---

## Troubleshooting

### Pi can't reach Mac Mini
```bash
tailscale status               # Both devices listed?
tailscale ping <mac-mini-hostname>   # Direct connectivity?
curl http://<MAC_MINI_TAILSCALE_IP>:18789  # Gateway responding?
```

### Scout won't start
```bash
journalctl -u <pi-hostname>-scout --no-pager -n 50   # Check error logs
python3 -m scout.main                          # Run manually to see errors
```

### Telegram alerts not sending
```bash
# Test the bot token directly
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getMe"
```
