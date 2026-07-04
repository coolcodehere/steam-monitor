"""Console entry point for check-page."""

import argparse
import sys
import urllib.error

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
        return 0

    print("unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


