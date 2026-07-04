"""Tests for waitlist / reserve signal detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pagemonitor.monitor import check_for_changes


def _html(body: str) -> bytes:
    return (
        "<!DOCTYPE html><html><head><title>test</title></head>"
        f"<body>{body}</body></html>"
    ).encode()


class CheckForChangesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.snapshot = Path(self._tmp.name) / "snapshot.html"
        self.url = "https://store.steampowered.com/hardware/steamframe"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @patch("pagemonitor.monitor.fetch_page")
    def test_first_run_creates_snapshot_without_alert(self, mock_fetch) -> None:
        mock_fetch.return_value = _html("<p>coming soon</p>")

        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)
        self.assertTrue(self.snapshot.exists())
        mock_fetch.assert_called_once_with(self.url)

    @patch("pagemonitor.monitor.fetch_page")
    def test_unrelated_body_change_does_not_alert(self, mock_fetch) -> None:
        mock_fetch.side_effect = [
            _html("<p>version 1</p>"),
            _html("<p>version 2</p>"),
        ]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)

    @patch("pagemonitor.discord.notify_page_change")
    @patch("pagemonitor.monitor.fetch_page")
    def test_new_reserve_signal_alerts(self, mock_fetch, mock_notify) -> None:
        mock_fetch.side_effect = [
            _html("<p>coming soon</p>"),
            _html('<a class="btn">Reserve</a>'),
        ]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertTrue(changed)
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.kwargs["signals"], ("reserve",))

    @patch("pagemonitor.discord.notify_page_change")
    @patch("pagemonitor.monitor.fetch_page")
    def test_new_waitlist_signal_alerts(self, mock_fetch, mock_notify) -> None:
        mock_fetch.side_effect = [
            _html("<p>coming soon</p>"),
            _html("<button>Join the Waitlist</button>"),
        ]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertTrue(changed)
        self.assertEqual(mock_notify.call_args.kwargs["signals"], ("waitlist",))

    @patch("pagemonitor.discord.notify_page_change")
    @patch("pagemonitor.monitor.fetch_page")
    def test_reserve_already_in_snapshot_does_not_realert(self, mock_fetch, mock_notify) -> None:
        page = _html('<a class="btn">Reserve</a>')
        mock_fetch.return_value = page

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)
        mock_notify.assert_not_called()

    @patch("urllib.request.urlopen")
    @patch("pagemonitor.monitor.fetch_page")
    def test_discord_api_called_on_new_signal(
        self,
        mock_fetch,
        mock_urlopen,
    ) -> None:
        import os

        mock_urlopen.return_value.__enter__.return_value.status = 200
        mock_fetch.side_effect = [
            _html("<p>coming soon</p>"),
            _html('<span>Reserve Now</span>'),
        ]
        with patch.dict(
            os.environ,
            {"DISCORD_BOT_TOKEN": "token", "DISCORD_CHANNEL_ID": "99"},
        ):
            check_for_changes(self.url, self.snapshot)
            check_for_changes(self.url, self.snapshot)

        self.assertEqual(mock_urlopen.call_count, 1)
        request = mock_urlopen.call_args[0][0]
        self.assertIn("/channels/99/messages", request.full_url)

    @patch("pagemonitor.discord.notify_page_change")
    @patch("pagemonitor.monitor.fetch_page")
    def test_does_not_notify_discord_without_new_signals(self, mock_fetch, mock_notify) -> None:
        page = _html("<p>hello</p>")
        mock_fetch.return_value = page

        check_for_changes(self.url, self.snapshot)
        check_for_changes(self.url, self.snapshot)

        mock_notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
