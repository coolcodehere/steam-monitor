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
    text = _DATA_CONFIG_ATTR_RE.sub("", text)
    text = _LARGE_DATA_ATTR_RE.sub("", text)
    text = _HEX_HASH_RE.sub('"<hash>"', text)
    text = _UNIX_TIMESTAMP_RE.sub("<ts>", text)
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
    old_tokens = _tokenize(old.decode("utf-8", errors="replace"))
    new_tokens = _tokenize(new.decode("utf-8", errors="replace"))
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)

    wrote_header = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if not wrote_header:
            out.write(f"--- {fromfile}\n")
            out.write(f"+++ {tofile}\n")
            wrote_header = True
        if tag in ("delete", "replace"):
            out.write(f"- {_join_tokens(old_tokens[i1:i2], max_chars=max_hunk_chars)}\n")
        if tag in ("insert", "replace"):
            out.write(f"+ {_join_tokens(new_tokens[j1:j2], max_chars=max_hunk_chars)}\n")


def check_for_changes(url: str, snapshot_path: str | Path) -> bool:
    """Fetch *url* and compare body content to the file at *snapshot_path*.

    Only the inner HTML inside ``<body>`` is compared and stored. Dynamic
    blocks (e.g. Steam ``application_config``), large ``data-*`` attributes,
    session hashes, and unix timestamps are stripped first. If no ``<body>``
    tag is found, the full response is used instead.

    - If the snapshot does not exist, write the normalized body and return ``False``.
    - If the snapshot exists and body content differs, print a compact diff
      of only the changed fragments, overwrite the snapshot, and return ``True``.
    - If body content is unchanged, return ``False``.
    """
    path = Path(snapshot_path)
    content = prepare_content(fetch_page(url))

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return False

    old = prepare_content(path.read_bytes())
    if old == content:
        return False

    print_diff(old, content, fromfile=str(path), tofile=url)
    path.write_bytes(content)
    return True
