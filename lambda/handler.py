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


def lambda_handler(event, context) -> dict[str, object]:
    bucket = os.environ["SNAPSHOT_BUCKET"]
    key = os.environ.get("SNAPSHOT_KEY", "snapshots/steamframe.html")
    url = os.environ.get(
        "PAGEMONITOR_URL",
        "https://store.steampowered.com/hardware/steamframe",
    )

    _download_snapshot(bucket, key, _LOCAL_SNAPSHOT)
    changed = check_for_changes(url, _LOCAL_SNAPSHOT)
    _upload_snapshot(bucket, key, _LOCAL_SNAPSHOT)

    return {
        "changed": changed,
        "url": url,
        "snapshot_key": key,
    }
