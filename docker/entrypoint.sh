#!/bin/sh
set -eu

URL="${PAGEMONITOR_URL:-https://store.steampowered.com/hardware/steamframe}"
SNAPSHOT="${PAGEMONITOR_SNAPSHOT:-/app/snapshots/steamframe.html}"
INTERVAL="${PAGEMONITOR_INTERVAL:-30}"

mkdir -p "$(dirname "$SNAPSHOT")"

echo "PageMonitor: ${URL}"
echo "Snapshot:  ${SNAPSHOT}"
echo "Interval:  ${INTERVAL}s"

if [ -n "${DISCORD_BOT_TOKEN:-}" ] && [ -n "${DISCORD_CHANNEL_ID:-}" ]; then
  echo "Discord: configured (channel ${DISCORD_CHANNEL_ID})"
  if [ -n "${DISCORD_NOTIFY_ROLE_ID:-}" ]; then
    echo "Discord: will @mention role ${DISCORD_NOTIFY_ROLE_ID} (@Steam Frame Interest) on Steam Frame changes"
  fi
  echo "Discord: messages are sent only when the page changes"
else
  echo "Discord: NOT configured — add DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID to .env, then recreate the container"
fi

while true; do
  date -u +"%Y-%m-%dT%H:%M:%SZ"
  python3 /app/scripts/check_page.py "$URL" "$SNAPSHOT" || true
  sleep "$INTERVAL"
done
