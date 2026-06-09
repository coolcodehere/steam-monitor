"""Fetch a web page and compare it to a local snapshot."""

from __future__ import annotations

import difflib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import TextIO

_BODY_RE = re.compile(
    r"<body\b[^>]*>(.*?)</body\s*>",
    re.IGNORECASE | re.DOTALL,
)
_APPLICATION_CONFIG_DIV_RE = re.compile(
    r'<div\b[^>]*\bid=["\']application_config["\'][^>]*>.*?</div\s*>',
    re.IGNORECASE | re.DOTALL,
)
_SCRIPT_TAG_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_DATA_CONFIG_ATTR_RE = re.compile(
    r'\sdata-config=(?:\"[^\"]*\"|\'[^\']*\')',
    re.IGNORECASE,
)
_LARGE_DATA_ATTR_RE = re.compile(
    r'\sdata-[a-z0-9_-]+=(?:\"[^\"]{200,}\"|\'[^\']{200,}\')',
    re.IGNORECASE,
)
_HEX_HASH_RE = re.compile(
    r'["\'][0-9a-f]{16,64}["\'];?',
    re.IGNORECASE,
)
_UNIX_TIMESTAMP_RE = re.compile(r"\b1\d{9}\b;?")
_URL_ATTR_RE = re.compile(
    r'(\s(?:href|src|srcset|action|poster|content|data-src|data-href|data-url|cite)\s*=\s*["\'])[^"\']*(["\'])',
    re.IGNORECASE,
)
_URL_ABSOLUTE_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_URL_PROTOCOL_RELATIVE_RE = re.compile(r"(?<!:)//[^\s\"'<>]+")

# (pattern, replacement) applied in order during normalize_body.
_VOLATILE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_URL_ATTR_RE, r"\1<url>\2"),
    (_URL_ABSOLUTE_RE, "<url>"),
    (_URL_PROTOCOL_RELATIVE_RE, "<url>"),
    (_HEX_HASH_RE, '"<hash>"'),
    (_UNIX_TIMESTAMP_RE, "<ts>"),
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


def normalize_body(content: bytes) -> bytes:
    """Remove volatile markup so incidental/session noise does not count as a change."""
    text = content.decode("utf-8", errors="replace")
    text = _APPLICATION_CONFIG_DIV_RE.sub("", text)
    text = _SCRIPT_TAG_RE.sub("", text)
    text = _DATA_CONFIG_ATTR_RE.sub("", text)
    text = _LARGE_DATA_ATTR_RE.sub("", text)
    for pattern, replacement in _VOLATILE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text.encode("utf-8")


def prepare_content(raw: bytes) -> bytes:
    """Extract body inner HTML and strip dynamic noise."""
    return normalize_body(extract_body(raw))


_TOKEN_RE = re.compile(r"<[^>]+>|\S+|\s+")
_MAX_HUNK_CHARS = 120


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _join_tokens(tokens: list[str], *, max_chars: int = _MAX_HUNK_CHARS) -> str:
    text = "".join(tokens)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}… ({len(text)} chars)"


def format_diff(
    old: bytes,
    new: bytes,
    *,
    fromfile: str = "snapshot",
    tofile: str = "fetched",
    max_hunk_chars: int = _MAX_HUNK_CHARS,
) -> str:
    """Return a compact diff of only the parts of the body that changed."""
    old_tokens = _tokenize(old.decode("utf-8", errors="replace"))
    new_tokens = _tokenize(new.decode("utf-8", errors="replace"))
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)

    lines: list[str] = []
    wrote_header = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if not wrote_header:
            lines.append(f"--- {fromfile}")
            lines.append(f"+++ {tofile}")
            wrote_header = True
        if tag in ("delete", "replace"):
            lines.append(f"- {_join_tokens(old_tokens[i1:i2], max_chars=max_hunk_chars)}")
        if tag in ("insert", "replace"):
            lines.append(f"+ {_join_tokens(new_tokens[j1:j2], max_chars=max_hunk_chars)}")
    return "\n".join(lines)


def print_diff(
    old: bytes,
    new: bytes,
    *,
    fromfile: str = "snapshot",
    tofile: str = "fetched",
    file: TextIO | None = None,
    max_hunk_chars: int = _MAX_HUNK_CHARS,
) -> None:
    """Print only the parts of the body that changed (not unchanged context)."""
    out = sys.stdout if file is None else file
    text = format_diff(
        old,
        new,
        fromfile=fromfile,
        tofile=tofile,
        max_hunk_chars=max_hunk_chars,
    )
    if text:
        out.write(text if text.endswith("\n") else f"{text}\n")


def check_for_changes(
    url: str,
    snapshot_path: str | Path,
    *,
    notify: bool = True,
) -> bool:
    """Fetch *url* and compare body content to the file at *snapshot_path*.

    Only the inner HTML inside ``<body>`` is compared and stored. Dynamic
    blocks (e.g. Steam ``application_config``), ``<script>`` tags, large ``data-*`` attributes,
    URLs in link attributes and absolute URLs, session hashes, and unix timestamps are stripped first.
    If no ``<body>``
    tag is found, the full response is used instead.

    - If the snapshot does not exist, write the normalized body and return ``False``.
    - If the snapshot exists and body content differs, print a compact diff,
      overwrite the snapshot, notify Discord, and return ``True``.
    - If body content is unchanged, return ``False``.

    Discord is notified only on **changes**. Posts go to ``DISCORD_CHANNEL_ID``;
    if ``DISCORD_NOTIFY_USER_ID`` is set, that user is @mentioned in the message.
    """
    from pagemonitor.env import load_dotenv

    load_dotenv()

    path = Path(snapshot_path)
    content = prepare_content(fetch_page(url))

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return False

    old = prepare_content(path.read_bytes())
    if old == content:
        return False

    diff_text = format_diff(old, content, fromfile=str(path), tofile=url)
    print_diff(old, content, fromfile=str(path), tofile=url)
    path.write_bytes(content)

    if notify:
        _maybe_notify_discord(
            url,
            changed=True,
            diff=diff_text,
            snapshot_path=str(path),
            page_content=content,
        )

    return True


def _maybe_notify_discord(
    url: str,
    *,
    changed: bool,
    diff: str,
    snapshot_path: str,
    baseline: bool = False,
    page_content: bytes | None = None,
) -> None:
    from pagemonitor.discord import DiscordError, DiscordNotConfigured, notify_page_change
    from pagemonitor.discord import notify_role_id, notify_user_id
    from pagemonitor.steamframe import should_alert_purchase, should_mention_role

    role_id = notify_role_id() if should_mention_role(url, changed=changed) else None
    purchase_alert = False
    if changed and page_content is not None:
        purchase_alert = should_alert_purchase(
            url,
            page_content,
            changed=True,
            diff=diff,
        )

    try:
        notify_page_change(
            url,
            changed=changed,
            diff=diff,
            snapshot_path=snapshot_path,
            baseline=baseline,
            mention_role_id=role_id,
            mention_user_id=notify_user_id(),
            purchase_alert=purchase_alert,
        )
        print("discord: message sent")
    except DiscordNotConfigured:
        print(
            "discord: not configured (set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in .env)",
            file=sys.stderr,
        )
    except DiscordError as exc:
        print(f"discord notification failed: {exc}", file=sys.stderr)
