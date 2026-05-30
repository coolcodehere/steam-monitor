#!/usr/bin/env python3
"""Send a test @mention to DISCORD_NOTIFY_USER_ID in the configured channel."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pagemonitor.discord import DiscordError, DiscordNotConfigured, ping_user


def main() -> int:
    try:
        ping_user()
    except DiscordNotConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except DiscordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
