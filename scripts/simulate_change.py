#!/usr/bin/env python3
"""Send a simulated Steam Frame change alert (reserve/buy detected) to Discord."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pagemonitor.discord import DiscordError, DiscordNotConfigured, notify_page_change, notify_role_id
from pagemonitor.steamframe import STEAM_FRAME_URL

_SAMPLE_DIFF = """\
--- snapshots/steamframe.html
+++ https://store.steampowered.com/hardware/steamframe
- <p>Notify me</p>
+ <a class="btn_green_steamui">Buy Now</a>"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post a fake page-change alert to Discord (does not fetch or update snapshots).",
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
    args = parser.parse_args()

    try:
        notify_page_change(
            args.url,
            changed=True,
            diff=_SAMPLE_DIFF,
            snapshot_path=args.snapshot,
            mention_role_id=notify_role_id(),
            purchase_alert=True,
        )
    except DiscordNotConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except DiscordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("sent simulated reserve/buy alert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
