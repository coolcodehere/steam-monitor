"""Tests for .env loading."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from pagemonitor.env import load_dotenv, reset_dotenv_cache


class LoadDotenvTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_dotenv_cache()
        os.environ.pop("PAGEMONITOR_TEST_KEY", None)

    def test_loads_variables_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text('PAGEMONITOR_TEST_KEY="hello"\n', encoding="utf-8")
            reset_dotenv_cache()
            loaded = load_dotenv(dotenv)
            self.assertTrue(loaded)
            self.assertEqual(os.environ["PAGEMONITOR_TEST_KEY"], "hello")

    def test_does_not_override_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("PAGEMONITOR_TEST_KEY=from_file\n", encoding="utf-8")
            os.environ["PAGEMONITOR_TEST_KEY"] = "from_shell"
            reset_dotenv_cache()
            load_dotenv(dotenv)
            self.assertEqual(os.environ["PAGEMONITOR_TEST_KEY"], "from_shell")

    def test_skips_comments_and_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text(
                "# comment\n\nPAGEMONITOR_TEST_KEY=value\n",
                encoding="utf-8",
            )
            reset_dotenv_cache()
            load_dotenv(dotenv)
            self.assertEqual(os.environ["PAGEMONITOR_TEST_KEY"], "value")


if __name__ == "__main__":
    unittest.main()
