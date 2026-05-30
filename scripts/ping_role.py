#!/usr/bin/env python3
"""Send a test @role message to the configured Discord channel."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pagemonitor.discord import DiscordError, DiscordNotConfigured, notify_role_id, ping_role


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a test Discord ping for the @Steam Frame Interest role.",
    )
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Message text (default mentions DISCORD_NOTIFY_ROLE_ID)",
    )
    args = parser.parse_args()

    try:
        ping_role(args.message)
    except DiscordNotConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except DiscordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    role_id = notify_role_id()
    print(f"sent (role id {role_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
