"""Load configuration from a .env file."""

from __future__ import annotations

import os
import re
from pathlib import Path

_LOADED = False
_LINE_RE = re.compile(
    r"""
    ^\s*
    (?P<key>[A-Za-z_][A-Za-z0-9_]*)
    \s*=\s*
    (?P<value>
        "(?:\\.|[^"\\])*"
        | '(?:\\.|[^'\\])*'
        | [^\s#]+
    )
    \s*
    (?:\#.*)?
    $
    """,
    re.VERBOSE,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_dotenv() -> Path | None:
    """Return the first existing ``.env`` in the cwd, container path, or project root."""
    candidates = (
        Path("/app/.env"),  # Docker volume mount
        Path.cwd() / ".env",
        project_root() / ".env",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        quote = value[0]
        inner = value[1:-1]
        return inner.replace(f"\\{quote}", quote)
    return value


def load_dotenv(
    path: str | Path | None = None,
    *,
    override: bool = False,
) -> bool:
    """Load ``KEY=VALUE`` pairs from a ``.env`` file into ``os.environ``.

    Existing environment variables are kept unless *override* is ``True``.
    Returns ``True`` if a file was loaded.
    """
    global _LOADED

    dotenv_path = Path(path) if path is not None else find_dotenv()
    if dotenv_path is None or not dotenv_path.is_file():
        return False

    if _LOADED and path is None and not override:
        return True

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if not match:
            continue
        key = match.group("key")
        value = _unquote(match.group("value"))
        if not override and key in os.environ:
            continue
        os.environ[key] = value

    if path is None:
        _LOADED = True
    return True


def reset_dotenv_cache() -> None:
    """Reset the load cache (for tests)."""
    global _LOADED
    _LOADED = False
