"""Steam Frame store page signal detection."""

from __future__ import annotations

import re
from urllib.parse import urlparse

STEAM_FRAME_URL = "https://store.steampowered.com/hardware/steamframe"

# Actionable waitlist / reserve UI — not FAQ prose or footer "rights reserved".
_SIGNAL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r">\s*Reserve(?:\s+Now)?\s*<", re.IGNORECASE), "reserve"),
    (re.compile(r">\s*Waitlist\s*<", re.IGNORECASE), "waitlist"),
    (re.compile(r">\s*Join\s+(?:the\s+)?Waitlist\s*<", re.IGNORECASE), "waitlist"),
    (re.compile(r"style=pill[^\]]*\]Reserve", re.IGNORECASE), "reserve"),
    (re.compile(r"style=pill[^\]]*\]Waitlist", re.IGNORECASE), "waitlist"),
    (re.compile(r"\bhardware_\w*reserve\w*", re.IGNORECASE), "reserve"),
    (re.compile(r"\bhardware_\w*waitlist\w*", re.IGNORECASE), "waitlist"),
)


def is_steamframe_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return (
        parsed.netloc.lower() in ("store.steampowered.com", "www.store.steampowered.com")
        and path == "/hardware/steamframe"
    )


def _signal_text(content: bytes | str) -> str:
    text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    return re.sub(r"rights\s+reserved", "", text, flags=re.IGNORECASE)


def detect_signals(content: bytes | str) -> frozenset[str]:
    """Return signal names (e.g. ``waitlist``, ``reserve``) present in *content*."""
    text = _signal_text(content)
    found: set[str] = set()
    for pattern, name in _SIGNAL_PATTERNS:
        if pattern.search(text):
            found.add(name)
    return frozenset(found)


def new_signals(old: bytes | str, new: bytes | str) -> frozenset[str]:
    """Return signals that appear in *new* but not in *old*."""
    return detect_signals(new) - detect_signals(old)


def should_mention_role(url: str, *, alert: bool) -> bool:
    """Mention the notify role when waitlist/reserve signals are newly detected."""
    return alert and is_steamframe_url(url)
