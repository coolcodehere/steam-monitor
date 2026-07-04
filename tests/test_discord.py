"""Tests for Discord notifications."""

from __future__ import annotations

import json
import os
import unittest
import urllib.request
from unittest.mock import MagicMock, patch

from pagemonitor.discord import (
    DiscordNotConfigured,
    _build_heartbeat_message,
    _build_message,
    notify_page_change,
    print_request,
    send_heartbeat,
    send_message,
)


class DiscordMessageTests(unittest.TestCase):
    def test_build_message_mentions_role_for_steamframe_alert(self) -> None:
        message = _build_message(
            "https://store.steampowered.com/hardware/steamframe",
            signals=("reserve",),
            snapshot_path="snapshots/steamframe.html",
            mention_role_id="987654321098765432",
        )
        self.assertTrue(message.startswith("<@&987654321098765432>"))
        self.assertIn("reserve detected", message)

    def test_build_message_includes_url(self) -> None:
        message = _build_message(
            "https://store.steampowered.com/hardware/steamframe",
            signals=("waitlist", "reserve"),
            snapshot_path="snapshots/steamframe.html",
        )
        self.assertIn("https://store.steampowered.com/hardware/steamframe", message)
        self.assertIn("waitlist, reserve detected", message)

    def test_build_message_truncates_long_header(self) -> None:
        message = _build_message(
            "https://example.com/" + "x" * 5000,
            signals=("reserve",),
            snapshot_path="snapshots/x.html",
        )
        self.assertLessEqual(len(message), 2000)

    def test_build_heartbeat_message_no_mentions(self) -> None:
        message = _build_heartbeat_message("https://store.steampowered.com/hardware/steamframe")
        self.assertIn("heartbeat", message)
        self.assertIn("No new waitlist/reserve signals", message)
        self.assertNotIn("<@&", message)
        self.assertNotIn("<@", message)


class DiscordHeartbeatTests(unittest.TestCase):
    @patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "DISCORD_CHANNEL_ID": "123"})
    @patch("pagemonitor.discord.print_request")
    @patch("urllib.request.urlopen")
    def test_send_heartbeat_posts_without_role_ping(
        self,
        mock_urlopen: MagicMock,
        _mock_print_request: MagicMock,
    ) -> None:
        mock_urlopen.return_value.__enter__.return_value.status = 200

        send_heartbeat("https://store.steampowered.com/hardware/steamframe")

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        self.assertIn("heartbeat", payload["content"])
        self.assertIn("No new waitlist/reserve signals", payload["content"])
        self.assertNotIn("allowed_mentions", payload)


class DiscordSendTests(unittest.TestCase):
    @patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "DISCORD_CHANNEL_ID": "123"})
    @patch("pagemonitor.discord.print_request")
    @patch("urllib.request.urlopen")
    def test_send_message_posts_to_channel(
        self,
        mock_urlopen: MagicMock,
        mock_print_request: MagicMock,
    ) -> None:
        mock_urlopen.return_value.__enter__.return_value.status = 200

        send_message("hello")

        mock_print_request.assert_called_once()

        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://discord.com/api/v10/channels/123/messages")
        self.assertEqual(request.get_header("Authorization"), "Bot token")
        payload = json.loads(request.data.decode())
        self.assertEqual(payload["content"], "hello")
        self.assertNotIn("allowed_mentions", payload)

    @patch.dict(
        os.environ,
        {
            "DISCORD_BOT_TOKEN": "token",
            "DISCORD_CHANNEL_ID": "123",
            "DISCORD_NOTIFY_USER_ID": "87620915126370304",
        },
    )
    @patch("pagemonitor.discord.print_request")
    @patch("urllib.request.urlopen")
    def test_send_message_allows_user_mention(
        self,
        mock_urlopen: MagicMock,
        _mock_print_request: MagicMock,
    ) -> None:
        mock_urlopen.return_value.__enter__.return_value.status = 200

        send_message("<@87620915126370304> hi", mention_user_ids=["87620915126370304"])

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        self.assertEqual(payload["allowed_mentions"], {"users": ["87620915126370304"]})

    @patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "DISCORD_CHANNEL_ID": "123"})
    @patch("pagemonitor.discord.print_request")
    @patch("urllib.request.urlopen")
    def test_send_message_allows_role_mention(
        self,
        mock_urlopen: MagicMock,
        _mock_print_request: MagicMock,
    ) -> None:
        mock_urlopen.return_value.__enter__.return_value.status = 200

        send_message("<@&987654321098765432> alert", mention_role_ids=["987654321098765432"])

        payload = json.loads(mock_urlopen.call_args[0][0].data.decode())
        self.assertEqual(payload["allowed_mentions"], {"roles": ["987654321098765432"]})

    @patch(
        "pagemonitor.discord._credentials",
        side_effect=DiscordNotConfigured("missing"),
    )
    def test_notify_requires_env(self, _mock_credentials) -> None:
        with self.assertRaises(DiscordNotConfigured):
            notify_page_change(
                "https://example.com",
                snapshot_path="snap.html",
            )

    def test_print_request_redacts_token(self) -> None:
        import io

        request = urllib.request.Request(
            "https://discord.com/api/v10/channels/1/messages",
            data=b'{"content":"hi"}',
            method="POST",
            headers={
                "Authorization": "Bot secret-token",
                "Content-Type": "application/json",
            },
        )
        buf = io.StringIO()
        print_request(request, file=buf)
        output = buf.getvalue()
        self.assertIn("POST https://discord.com/api/v10/channels/1/messages", output)
        self.assertIn("Bot ***", output)
        self.assertNotIn("secret-token", output)
        self.assertIn('body: {"content":"hi"}', output)


if __name__ == "__main__":
    unittest.main()
