#!/bin/sh
set -eu

URL="${PAGEMONITOR_URL:-https://store.steampowered.com/hardware/steamframe}"
SNAPSHOT="${PAGEMONITOR_SNAPSHOT:-/app/snapshots/steamframe.html}"
INTERVAL="${PAGEMONITOR_INTERVAL:-30}"
HEARTBEAT_INTERVAL="${PAGEMONITOR_HEARTBEAT_INTERVAL:-21600}"
LAST_HEARTBEAT_FILE="$(dirname "$SNAPSHOT")/.last_heartbeat"

mkdir -p "$(dirname "$SNAPSHOT")"

echo "PageMonitor: ${URL}"
echo "Snapshot:  ${SNAPSHOT}"
echo "Interval:  ${INTERVAL}s"
echo "Heartbeat: every ${HEARTBEAT_INTERVAL}s"

if [ -n "${DISCORD_BOT_TOKEN:-}" ] && [ -n "${DISCORD_CHANNEL_ID:-}" ]; then
  echo "Discord: configured (channel ${DISCORD_CHANNEL_ID})"
  if [ -n "${DISCORD_NOTIFY_ROLE_ID:-}" ]; then
    echo "Discord: will @mention role ${DISCORD_NOTIFY_ROLE_ID} (@Steam Frame Interest) on waitlist/reserve signals"
  fi
  echo "Discord: heartbeat every ${HEARTBEAT_INTERVAL}s (no role ping)"
else
  echo "Discord: NOT configured — add DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID to .env, then recreate the container"
fi

while true; do
  date -u +"%Y-%m-%dT%H:%M:%SZ"
  python3 /app/scripts/check_page.py "$URL" "$SNAPSHOT" || true

  now=$(date +%s)
  last=0
  if [ -f "$LAST_HEARTBEAT_FILE" ]; then
    last=$(cat "$LAST_HEARTBEAT_FILE")
  fi
  if [ "$((now - last))" -ge "$HEARTBEAT_INTERVAL" ]; then
    if python3 /app/scripts/heartbeat.py "$URL"; then
      echo "$now" > "$LAST_HEARTBEAT_FILE"
    fi
  fi

  sleep "$INTERVAL"
done
