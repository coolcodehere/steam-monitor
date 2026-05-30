"""Tests for Steam Frame purchase detection."""

from __future__ import annotations

import unittest

from pagemonitor.steamframe import (
    STEAM_FRAME_URL,
    has_purchase_option,
    is_steamframe_url,
    purchase_added_in_diff,
    should_alert_purchase,
    should_mention_role,
)


class SteamframeUrlTests(unittest.TestCase):
    def test_recognizes_steamframe_url(self) -> None:
        self.assertTrue(is_steamframe_url(STEAM_FRAME_URL))
        self.assertTrue(is_steamframe_url(STEAM_FRAME_URL + "/"))

    def test_rejects_other_urls(self) -> None:
        self.assertFalse(is_steamframe_url("https://store.steampowered.com/app/730"))


class PurchaseDetectionTests(unittest.TestCase):
    def test_ignores_rights_reserved(self) -> None:
        html = b"<p>All rights reserved. Valve Corporation.</p>"
        self.assertFalse(has_purchase_option(html))

    def test_detects_reserve_button(self) -> None:
        html = b'<div class="purchase"><a>Reserve</a></div>'
        self.assertTrue(has_purchase_option(html))

    def test_detects_buy_now_button(self) -> None:
        html = b'<span class="btn">Buy Now</span>'
        self.assertTrue(has_purchase_option(html))

    def test_detects_purchase_in_diff(self) -> None:
        diff = "--- old\n+++ new\n- <p>Coming soon</p>\n+ <a>Buy Now</a>"
        self.assertTrue(purchase_added_in_diff(diff))

    def test_should_mention_role_on_steamframe_change(self) -> None:
        self.assertTrue(should_mention_role(STEAM_FRAME_URL, changed=True))

    def test_should_not_mention_role_when_unchanged(self) -> None:
        self.assertFalse(should_mention_role(STEAM_FRAME_URL, changed=False))

    def test_should_not_mention_role_for_other_urls(self) -> None:
        self.assertFalse(
            should_mention_role("https://store.steampowered.com/app/730", changed=True),
        )

    def test_should_alert_purchase_on_steamframe_change_with_buy(self) -> None:
        content = b'<button>Buy Now</button>'
        self.assertTrue(
            should_alert_purchase(
                STEAM_FRAME_URL,
                content,
                changed=True,
                diff="",
            ),
        )

    def test_should_not_alert_purchase_without_purchase_signal(self) -> None:
        content = b"<p>Specs updated</p>"
        self.assertFalse(
            should_alert_purchase(
                STEAM_FRAME_URL,
                content,
                changed=True,
                diff="--- a\n+++ b\n- old\n+ new",
            ),
        )


if __name__ == "__main__":
    unittest.main()
