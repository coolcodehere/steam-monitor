"""Fetch a web page and detect waitlist / reserve signals."""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

_BODY_RE = re.compile(
    r"<body\b[^>]*>(.*?)</body\s*>",
    re.IGNORECASE | re.DOTALL,
)


def fetch_page(url: str, *, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PageMonitor/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def extract_body(content: bytes) -> bytes:
    """Return the inner HTML of the first ``<body>`` element, or *content* unchanged."""
    text = content.decode("utf-8", errors="replace")
    match = _BODY_RE.search(text)
    if match is None:
        return content
    return match.group(1).encode("utf-8")


def prepare_content(raw: bytes) -> bytes:
    """Extract body inner HTML for signal detection."""
    return extract_body(raw)


def check_for_changes(
    url: str,
    snapshot_path: str | Path,
    *,
    notify: bool = True,
) -> bool:
    """Fetch *url* and detect newly appeared waitlist / reserve signals.

    Only the inner HTML inside ``<body>`` is stored in the snapshot. If no
    ``<body>`` tag is found, the full response is used instead.

    - If the snapshot does not exist, write the body and return ``False``.
    - If new waitlist / reserve signals appear vs the snapshot, notify Discord
      and return ``True``.
    - Otherwise update the snapshot and return ``False``.
    """
    from pagemonitor.env import load_dotenv
    from pagemonitor.steamframe import new_signals

    load_dotenv()

    path = Path(snapshot_path)
    content = prepare_content(fetch_page(url))

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return False

    old = path.read_bytes()
    appeared = new_signals(old, content)
    path.write_bytes(content)

    if not appeared:
        return False

    if notify:
        _maybe_notify_discord(
            url,
            signals=tuple(sorted(appeared)),
            snapshot_path=str(path),
        )

    return True


def _maybe_notify_discord(
    url: str,
    *,
    signals: tuple[str, ...],
    snapshot_path: str,
) -> None:
    from pagemonitor.discord import DiscordError, DiscordNotConfigured, notify_page_change
    from pagemonitor.discord import notify_role_id, notify_user_id
    from pagemonitor.steamframe import should_mention_role

    alert = bool(signals)
    role_id = notify_role_id() if should_mention_role(url, alert=alert) else None

    try:
        notify_page_change(
            url,
            signals=signals,
            snapshot_path=snapshot_path,
            mention_role_id=role_id,
            mention_user_id=notify_user_id(),
        )
        print("discord: message sent")
    except DiscordNotConfigured:
        print(
            "discord: not configured (set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in .env)",
            file=sys.stderr,
        )
    except DiscordError as exc:
        print(f"discord notification failed: {exc}", file=sys.stderr)
