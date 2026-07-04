"""AWS Lambda entry point: sync snapshot from S3, run check, sync back."""

from __future__ import annotations

import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from pagemonitor.monitor import check_for_changes

_s3 = boto3.client("s3")
_LOCAL_SNAPSHOT = Path("/tmp/steamframe.html")


def _download_snapshot(bucket: str, key: str, local: Path) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        _s3.download_file(bucket, key, str(local))
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return
        raise


def _upload_snapshot(bucket: str, key: str, local: Path) -> None:
    if local.is_file():
        _s3.upload_file(str(local), bucket, key)


def _monitor_url() -> str:
    return os.environ.get(
        "PAGEMONITOR_URL",
        "https://store.steampowered.com/hardware/steamframe",
    )


def _run_check() -> dict[str, object]:
    bucket = os.environ["SNAPSHOT_BUCKET"]
    key = os.environ.get("SNAPSHOT_KEY", "snapshots/steamframe.html")
    url = _monitor_url()

    _download_snapshot(bucket, key, _LOCAL_SNAPSHOT)
    changed = check_for_changes(url, _LOCAL_SNAPSHOT)
    _upload_snapshot(bucket, key, _LOCAL_SNAPSHOT)

    return {
        "changed": changed,
        "url": url,
        "snapshot_key": key,
        "task": "check",
    }


def _run_heartbeat() -> dict[str, object]:
    from pagemonitor.discord import DiscordError, DiscordNotConfigured, send_heartbeat

    url = _monitor_url()
    try:
        send_heartbeat(url)
    except DiscordNotConfigured:
        return {"heartbeat": False, "url": url, "task": "heartbeat", "reason": "not_configured"}
    except DiscordError as exc:
        return {"heartbeat": False, "url": url, "task": "heartbeat", "reason": str(exc)}

    return {"heartbeat": True, "url": url, "task": "heartbeat"}


def lambda_handler(event, context) -> dict[str, object]:
    if event.get("task") == "heartbeat":
        return _run_heartbeat()
    return _run_check()
