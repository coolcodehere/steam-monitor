#!/usr/bin/env python3
"""Send a simulated Steam Frame waitlist/reserve alert to Discord."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pagemonitor.discord import DiscordError, DiscordNotConfigured, notify_page_change, notify_role_id
from pagemonitor.steamframe import STEAM_FRAME_URL


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post a fake waitlist/reserve alert to Discord (does not fetch or update snapshots).",
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=STEAM_FRAME_URL,
        help="Page URL shown in the alert",
    )
    parser.add_argument(
        "snapshot",
        nargs="?",
        default="snapshots/steamframe.html",
        help="Snapshot path shown in the alert",
    )
    parser.add_argument(
        "--signal",
        action="append",
        default=["reserve"],
        choices=("waitlist", "reserve"),
        help="Signal name(s) to include in the alert (repeatable)",
    )
    args = parser.parse_args()

    try:
        notify_page_change(
            args.url,
            signals=tuple(sorted(set(args.signal))),
            snapshot_path=args.snapshot,
            mention_role_id=notify_role_id(),
        )
    except DiscordNotConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except DiscordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("sent simulated waitlist/reserve alert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
