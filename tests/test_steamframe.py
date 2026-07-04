"""Tests for Steam Frame signal detection."""

from __future__ import annotations

import unittest

from pagemonitor.steamframe import (
    STEAM_FRAME_URL,
    detect_signals,
    is_steamframe_url,
    new_signals,
    should_mention_role,
)


class SteamframeUrlTests(unittest.TestCase):
    def test_recognizes_steamframe_url(self) -> None:
        self.assertTrue(is_steamframe_url(STEAM_FRAME_URL))
        self.assertTrue(is_steamframe_url(STEAM_FRAME_URL + "/"))

    def test_rejects_other_urls(self) -> None:
        self.assertFalse(is_steamframe_url("https://store.steampowered.com/app/730"))


class SignalDetectionTests(unittest.TestCase):
    def test_ignores_rights_reserved(self) -> None:
        html = b"<p>All rights reserved. Valve Corporation.</p>"
        self.assertEqual(detect_signals(html), frozenset())

    def test_detects_reserve_button(self) -> None:
        html = b'<div class="purchase"><a>Reserve</a></div>'
        self.assertEqual(detect_signals(html), frozenset({"reserve"}))

    def test_detects_waitlist_button(self) -> None:
        html = b'<button>Join the Waitlist</button>'
        self.assertEqual(detect_signals(html), frozenset({"waitlist"}))

    def test_detects_pill_style_reserve(self) -> None:
        html = b'[url="https://example.com" style=pill]Reserve Now[/url]'
        self.assertEqual(detect_signals(html), frozenset({"reserve"}))

    def test_new_signals_only_returns_appeared(self) -> None:
        old = b"<p>coming soon</p>"
        new = b'<a>Reserve</a>'
        self.assertEqual(new_signals(old, new), frozenset({"reserve"}))

    def test_should_mention_role_on_alert(self) -> None:
        self.assertTrue(should_mention_role(STEAM_FRAME_URL, alert=True))

    def test_should_not_mention_role_without_alert(self) -> None:
        self.assertFalse(should_mention_role(STEAM_FRAME_URL, alert=False))

    def test_should_not_mention_role_for_other_urls(self) -> None:
        self.assertFalse(
            should_mention_role("https://store.steampowered.com/app/730", alert=True),
        )


if __name__ == "__main__":
    unittest.main()
