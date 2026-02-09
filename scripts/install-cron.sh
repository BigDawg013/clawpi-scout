#!/usr/bin/env bash
set -euo pipefail

SCOUT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$SCOUT_DIR/.venv/bin/python"

echo "=== clawpi-scout cron installer ==="

# Morning briefing at 8:00 AM every day
CRON_BRIEFING="0 8 * * * cd $SCOUT_DIR && $PYTHON -m scout.briefing >> /tmp/clawpi-scout-briefing.log 2>&1"

# Install cron jobs (preserve existing, avoid duplicates)
( (crontab -l 2>/dev/null || true) | grep -v "scout.briefing" ; echo "$CRON_BRIEFING") | crontab -

echo "Cron jobs installed:"
crontab -l | grep scout
echo ""
echo "Morning briefing will run daily at 8:00 AM."
echo "Test it now:  cd $SCOUT_DIR && $PYTHON -m scout.briefing"
