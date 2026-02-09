#!/usr/bin/env bash
set -euo pipefail

SCOUT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="clawpi-scout"

echo "=== clawpi-scout installer ==="
echo "Project: $SCOUT_DIR"

# Python venv
echo "[1/4] Creating virtual environment..."
python3 -m venv "$SCOUT_DIR/.venv"
source "$SCOUT_DIR/.venv/bin/activate"

echo "[2/4] Installing dependencies..."
pip install --upgrade pip -q
pip install -r "$SCOUT_DIR/requirements.txt" -q

# systemd service
echo "[3/4] Installing systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=clawpi-scout — OpenClaw scout daemon
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCOUT_DIR
ExecStart=$SCOUT_DIR/.venv/bin/python -m scout.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "[4/4] Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}

echo ""
echo "=== Done ==="
echo "Next steps:"
echo "  1. Edit config/scout.yaml with your tokens and targets"
echo "  2. sudo systemctl start ${SERVICE_NAME}"
echo "  3. journalctl -u ${SERVICE_NAME} -f"
