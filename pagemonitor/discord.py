"""Send change notifications via the Discord bot API."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import TextIO

_DISCORD_API = "https://discord.com/api/v10"
_MAX_MESSAGE_LEN = 2000
_MENTION_RE = re.compile(r"<@!?(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")
STEAM_FRAME_INTEREST_ROLE_NAME = "Steam Frame Interest"


class DiscordError(Exception):
    """Discord API or configuration error."""


class DiscordNotConfigured(DiscordError):
    """Required Discord environment variables are missing."""


def _credentials() -> tuple[str, str]:
    from pagemonitor.env import load_dotenv

    load_dotenv()
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("DISCORD_CHANNEL_ID", "").strip()
    if not token or not channel_id:
        raise DiscordNotConfigured(
            "set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in .env to enable notifications",
        )
    return token, channel_id


def notify_user_id() -> str | None:
    """Discord user ID to @mention in the configured channel (optional)."""
    from pagemonitor.env import load_dotenv

    load_dotenv()
    user_id = os.environ.get("DISCORD_NOTIFY_USER_ID", "").strip()
    return user_id or None


def notify_role_id() -> str | None:
    """Discord role ID for @Steam Frame Interest (optional)."""
    from pagemonitor.env import load_dotenv

    load_dotenv()
    role_id = os.environ.get("DISCORD_NOTIFY_ROLE_ID", "").strip()
    return role_id or None


def _allowed_mentions(
    *,
    role_ids: list[str],
    user_ids: list[str],
) -> dict[str, object] | None:
    payload: dict[str, object] = {}
    if role_ids:
        payload["roles"] = role_ids
    if user_ids:
        payload["users"] = user_ids
    return payload or None


def _user_ids_from_content(content: str, extra: str | None = None) -> list[str]:
    ids = list(_MENTION_RE.findall(content))
    if extra:
        ids.append(extra)
    return list(dict.fromkeys(ids))


def _role_ids_from_content(content: str, extra: str | None = None) -> list[str]:
    ids = list(_ROLE_MENTION_RE.findall(content))
    if extra:
        ids.append(extra)
    return list(dict.fromkeys(ids))


def _build_message(
    url: str,
    *,
    changed: bool,
    diff: str,
    snapshot_path: str,
    baseline: bool = False,
    mention_role_id: str | None = None,
    mention_user_id: str | None = None,
    purchase_alert: bool = False,
) -> str:
    role_prefix = f"<@&{mention_role_id}> " if mention_role_id and changed else ""
    user_prefix = f"<@{mention_user_id}> " if mention_user_id and changed else ""

    if baseline:
        header = f"{user_prefix}**Baseline saved**\n{url}\nSnapshot: `{snapshot_path}`"
    elif changed:
        if purchase_alert:
            title = "**Steam Frame: reserve / buy detected**"
        else:
            title = "**Page changed**"
        header = f"{role_prefix}{user_prefix}{title}\n{url}\nSnapshot: `{snapshot_path}`"
    else:
        header = f"**No changes**\n{url}\nSnapshot: `{snapshot_path}`"

    if not changed or not diff:
        return header[:_MAX_MESSAGE_LEN]

    block_start = f"{header}\n```diff\n"
    block_end = "\n```"
    budget = _MAX_MESSAGE_LEN - len(block_start) - len(block_end)
    if budget < 1:
        return header[:_MAX_MESSAGE_LEN]

    trimmed = diff if len(diff) <= budget else f"{diff[: budget - 1]}…"
    return f"{block_start}{trimmed}{block_end}"[:_MAX_MESSAGE_LEN]


def print_request(request: urllib.request.Request, *, file: TextIO = sys.stdout) -> None:
    """Print the Discord API request to the console (token redacted)."""
    file.write("Discord API request:\n")
    file.write(f"  {request.method} {request.full_url}\n")
    for key, value in request.header_items():
        if key.lower() == "authorization":
            value = "Bot ***"
        file.write(f"  {key}: {value}\n")
    if request.data:
        file.write(f"  body: {request.data.decode('utf-8')}\n")


def send_message(
    content: str,
    *,
    token: str | None = None,
    channel_id: str | None = None,
    log_request: bool = True,
    mention_role_ids: list[str] | None = None,
    mention_user_ids: list[str] | None = None,
) -> None:
    """Post *content* to a channel using the Discord bot API."""
    bot_token, chan_id = _credentials()
    if token is not None:
        bot_token = token
    if channel_id is not None:
        chan_id = channel_id

    role_ids = list(mention_role_ids or [])
    role_ids = list(dict.fromkeys(_role_ids_from_content(content, None) + role_ids))
    user_ids = list(mention_user_ids or [])
    user_ids = list(dict.fromkeys(_user_ids_from_content(content, None) + user_ids))

    payload: dict[str, object] = {"content": content[:_MAX_MESSAGE_LEN]}
    allowed = _allowed_mentions(role_ids=role_ids, user_ids=user_ids)
    if allowed:
        payload["allowed_mentions"] = allowed

    body_bytes = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{_DISCORD_API}/channels/{chan_id}/messages",
        data=body_bytes,
        method="POST",
        headers={
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "PageMonitor/1.0 (Discord notifications)",
        },
    )
    if log_request:
        print_request(request)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status >= 400:
                raise DiscordError(f"Discord API returned status {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DiscordError(f"Discord API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DiscordError(str(exc)) from exc


def notify_page_change(
    url: str,
    *,
    changed: bool,
    diff: str = "",
    snapshot_path: str,
    baseline: bool = False,
    mention_role_id: str | None = None,
    mention_user_id: str | None = None,
    purchase_alert: bool = False,
) -> None:
    """Post the result of a page check to Discord."""
    token, channel_id = _credentials()
    user_id = mention_user_id if mention_user_id is not None else notify_user_id()
    role_id = mention_role_id if mention_role_id is not None else None
    message = _build_message(
        url,
        changed=changed,
        diff=diff,
        snapshot_path=snapshot_path,
        baseline=baseline,
        mention_role_id=role_id,
        mention_user_id=user_id,
        purchase_alert=purchase_alert,
    )
    role_ids = [role_id] if role_id else []
    user_ids = [user_id] if user_id else []
    send_message(
        message,
        token=token,
        channel_id=channel_id,
        mention_role_ids=role_ids,
        mention_user_ids=user_ids,
    )


def ping_role(message: str | None = None) -> None:
    """Send a test message that @mentions the configured notify role."""
    role_id = notify_role_id()
    if not role_id:
        raise DiscordNotConfigured("set DISCORD_NOTIFY_ROLE_ID in .env")
    text = message or f"<@&{role_id}> PageMonitor test ping."
    send_message(text, mention_role_ids=[role_id])


def ping_user(message: str | None = None) -> None:
    """Send a test message in the channel that @mentions DISCORD_NOTIFY_USER_ID."""
    user_id = notify_user_id()
    if not user_id:
        raise DiscordNotConfigured("set DISCORD_NOTIFY_USER_ID in .env")
    text = message or f"<@{user_id}> PageMonitor test ping."
    send_message(text, mention_user_ids=[user_id])
