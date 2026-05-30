"""Tests for page change detection."""

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
        self.url = "http://example.test/page"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @patch("pagemonitor.monitor.fetch_page")
    def test_first_run_creates_snapshot_without_change(self, mock_fetch) -> None:
        mock_fetch.return_value = _html("<p>hello</p>")

        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)
        self.assertTrue(self.snapshot.exists())
        self.assertIn(b"hello", self.snapshot.read_bytes())
        mock_fetch.assert_called_once_with(self.url)

    @patch("pagemonitor.monitor.fetch_page")
    def test_same_content_on_second_run_is_unchanged(self, mock_fetch) -> None:
        page = _html("<p>hello</p>")
        mock_fetch.return_value = page

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("pagemonitor.monitor.print_diff")
    @patch("pagemonitor.monitor.fetch_page")
    def test_injected_body_change_returns_true(self, mock_fetch, _mock_diff) -> None:
        mock_fetch.side_effect = [
            _html("<p>version 1</p>"),
            _html("<p>version 2</p>"),
        ]

        baseline = check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(baseline)
        self.assertTrue(changed)
        self.assertIn(b"version 2", self.snapshot.read_bytes())
        self.assertNotIn(b"version 1", self.snapshot.read_bytes())

    @patch("pagemonitor.monitor.fetch_page")
    def test_session_noise_does_not_trigger_change(self, mock_fetch) -> None:
        mock_fetch.side_effect = [
            _html(
                '<p>product</p>'
                '<script>token = "aaaaaaaaaaaaaaaaaaaaaaaa"; ts = 1780164592;</script>'
            ),
            _html(
                '<p>product</p>'
                '<script>token = "bbbbbbbbbbbbbbbbbbbbbbbb"; ts = 1780164680;</script>'
            ),
        ]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
