"""Tests for page change detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pagemonitor.monitor import check_for_changes, normalize_body


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

    @patch("pagemonitor.discord.notify_page_change")
    @patch("pagemonitor.monitor.print_diff")
    @patch("pagemonitor.monitor.fetch_page")
    def test_injected_body_change_returns_true(
        self,
        mock_fetch,
        _mock_diff,
        mock_notify,
    ) -> None:
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
        mock_notify.assert_called_once()
        self.assertTrue(mock_notify.call_args.kwargs["changed"])
        self.assertIn("2</p>", mock_notify.call_args.kwargs["diff"])

    @patch("urllib.request.urlopen")
    @patch("pagemonitor.monitor.fetch_page")
    def test_discord_api_called_on_change(
        self,
        mock_fetch,
        mock_urlopen,
    ) -> None:
        import os

        mock_urlopen.return_value.__enter__.return_value.status = 200
        mock_fetch.side_effect = [
            _html("<p>v1</p>"),
            _html("<p>v2</p>"),
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
    def test_does_not_notify_discord_when_unchanged(self, mock_fetch, mock_notify) -> None:
        page = _html("<p>hello</p>")
        mock_fetch.return_value = page

        check_for_changes(self.url, self.snapshot)
        check_for_changes(self.url, self.snapshot)

        mock_notify.assert_not_called()

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

    @patch("pagemonitor.monitor.fetch_page")
    def test_script_src_changes_do_not_trigger_change(self, mock_fetch) -> None:
        mock_fetch.side_effect = [
            _html(
                '<p>product</p>'
                '<script type="text/javascript" src="https://cdn.example/manifest.js?v=abc123"></script>'
                '<script type="text/javascript" src="https://cdn.example/main.js?v=1.0.0"></script>'
            ),
            _html(
                '<p>product</p>'
                '<script type="text/javascript" src="https://cdn.example/manifest.js?v=def456"></script>'
                '<script type="text/javascript" src="https://cdn.example/main.js?v=1.0.1"></script>'
            ),
        ]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)

    @patch("pagemonitor.monitor.fetch_page")
    def test_steam_cdn_host_rotation_does_not_trigger_change(self, mock_fetch) -> None:
        akamai = (
            '<img src="https://store.akamai.steamstatic.com/public/shared/images/header/logo_steam.svg">'
            '<link href="https://store.akamai.steamstatic.com/public/css/applications/store/main.css?v=abc&amp;l=english">'
        )
        fastly = (
            '<img src="https://store.fastly.steamstatic.com/public/shared/images/header/logo_steam.svg">'
            '<link href="https://store.fastly.steamstatic.com/public/css/applications/store/main.css?v=abc&amp;l=english">'
        )
        mock_fetch.side_effect = [_html(akamai), _html(fastly)]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)

    def test_normalize_body_strips_urls(self) -> None:
        raw = (
            b'<img src="https://store.akamai.steamstatic.com/foo.png">'
            b'<link href="https://store.fastly.steamstatic.com/bar.css?v=1">'
        )
        normalized = normalize_body(raw).decode()
        self.assertIn('src="<url>"', normalized)
        self.assertIn('href="<url>"', normalized)
        self.assertNotIn("steamstatic", normalized)

    @patch("pagemonitor.monitor.fetch_page")
    def test_asset_url_changes_do_not_trigger_change(self, mock_fetch) -> None:
        first = (
            '<link href="https://store.fastly.steamstatic.com/public/css/applications/store/'
            'main.css?v=yF84mF-QAmvP&amp;l=english&amp;_cdn=fastly">'
        )
        second = (
            '<link href="https://store.akamai.steamstatic.com/public/css/applications/store/'
            'main.css?v=ZC-rseGiB9hA&amp;l=english&amp;_cdn=akamai">'
        )
        mock_fetch.side_effect = [_html(first), _html(second)]

        check_for_changes(self.url, self.snapshot)
        changed = check_for_changes(self.url, self.snapshot)

        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
