#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${PAGEMONITOR_ENV:-$ROOT/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "error: missing $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
. "$ENV_FILE"
set +a

if [ -z "${DISCORD_BOT_TOKEN:-}" ] || [ -z "${DISCORD_CHANNEL_ID:-}" ]; then
  echo "error: DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID must be set in $ENV_FILE" >&2
  exit 1
fi

sam build
sam deploy \
  --parameter-overrides \
    "DiscordBotToken=${DISCORD_BOT_TOKEN}" \
    "DiscordChannelId=${DISCORD_CHANNEL_ID}" \
    "DiscordNotifyRoleId=${DISCORD_NOTIFY_ROLE_ID:-}"
