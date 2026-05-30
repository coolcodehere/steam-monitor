"""Steam Frame store page helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

STEAM_FRAME_URL = "https://store.steampowered.com/hardware/steamframe"

# Visible purchase actions and Steam store purchase markup.
_PURCHASE_SIGNALS = (
    re.compile(r">\s*Reserve(?:\s+Now)?\s*<", re.IGNORECASE),
    re.compile(r">\s*Buy(?:\s+Now)?\s*<", re.IGNORECASE),
    re.compile(r">\s*Pre-?order(?:\s+Now)?\s*<", re.IGNORECASE),
    re.compile(r">\s*Add\s+to\s+Cart\s*<", re.IGNORECASE),
    re.compile(r"\bbtn_addtocart\b", re.IGNORECASE),
    re.compile(r"\bgame_purchase_\w+", re.IGNORECASE),
    re.compile(r"\bhardware_\w*(?:buy|reserve|purchase)\w*", re.IGNORECASE),
    re.compile(r"\bAddToCart\b"),
    re.compile(r'"add_to_cart"\s*:', re.IGNORECASE),
    re.compile(r"data-price-final", re.IGNORECASE),
    re.compile(r'\[\/url\]\s*Buy\s+Now\s*\[', re.IGNORECASE),
    re.compile(r"style=pill[^\]]*\]Reserve", re.IGNORECASE),
    re.compile(r"style=pill[^\]]*\]Buy\s+Now", re.IGNORECASE),
)


def is_steamframe_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return (
        parsed.netloc.lower() in ("store.steampowered.com", "www.store.steampowered.com")
        and path == "/hardware/steamframe"
    )


def _purchase_text(content: bytes | str) -> str:
    text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    return re.sub(r"rights\s+reserved", "", text, flags=re.IGNORECASE)


def has_purchase_option(content: bytes | str) -> bool:
    """Return True if *content* looks like it offers reserve or buy."""
    text = _purchase_text(content)
    return any(pattern.search(text) for pattern in _PURCHASE_SIGNALS)


def purchase_added_in_diff(diff: str) -> bool:
    """Return True if added diff lines introduce a reserve/buy signal."""
    added = "\n".join(
        line[2:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    if not added.strip():
        return False
    return has_purchase_option(added)


def should_mention_role(url: str, *, changed: bool) -> bool:
    """Mention @Steam Frame Interest when the Steam Frame page changes."""
    return changed and is_steamframe_url(url)


def should_alert_purchase(
    url: str,
    content: bytes,
    *,
    changed: bool,
    diff: str = "",
) -> bool:
    """Use reserve/buy headline when purchase signals appear on a Steam Frame change."""
    if not changed or not is_steamframe_url(url):
        return False
    return has_purchase_option(content) or purchase_added_in_diff(diff)
