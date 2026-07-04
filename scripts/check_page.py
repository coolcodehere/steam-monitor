#!/usr/bin/env python3
"""CLI: fetch a URL, compare to a local snapshot, update on change."""

import argparse
import sys
import urllib.error
from pathlib import Path

# Allow running without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pagemonitor.monitor import check_for_changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a web page and detect waitlist/reserve signals against a local snapshot.",
    )
    parser.add_argument("url", help="Page URL to fetch")
    parser.add_argument(
        "snapshot",
        help="Path to the local snapshot file",
    )
    args = parser.parse_args()

    try:
        changed = check_for_changes(args.url, args.snapshot)
    except urllib.error.URLError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if changed:
        print("alert: new waitlist/reserve signal(s)")
        return 0

    print("no new waitlist/reserve signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
