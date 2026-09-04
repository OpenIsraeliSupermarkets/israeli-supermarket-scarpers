"""Tests that FTP listing yields files before the directory scan finishes."""
# pylint: disable=missing-function-docstring

import asyncio
import threading
import unittest
from unittest.mock import patch

from ftplib import error_perm

from il_supermarket_scarper.utils.connection import collect_from_ftp


class _FakeMlsdFtp:
    """FTP_TLS stand-in whose MLSD iterator can block mid-listing."""

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        self.trust_server_pasv_ipv4_address = False
        self.closed = False

    def cwd(self, path):  # pylint: disable=unused-argument
        """Change directory (no-op)."""
        return None

    def mlsd(self):
        """Yield no entries unless a subclass overrides."""
        return iter(())

    def quit(self):
        """Mark the fake connection closed."""
        self.closed = True

    def close(self):
        """Mark the fake connection closed."""
        self.closed = True


class TestFtpStreaming(unittest.IsolatedAsyncioTestCase):
    """Verify collect_from_ftp streams entries instead of buffering the listing."""

    async def test_yields_before_mlsd_finishes(self):
        """The first file must appear while a later MLSD entry is still blocked."""
        started = threading.Event()
        release = threading.Event()

        class SlowMlsd(_FakeMlsdFtp):
            """MLSD that blocks after the first file."""
            def mlsd(self):
                yield ("fast.xml", {"type": "file", "size": "10"})
                started.set()
                release.wait(timeout=5)
                yield ("dir-a", {"type": "dir"})
                yield ("slow.xml", {"type": "file", "size": "20"})

        with patch(
            "il_supermarket_scarper.utils.connection.FTP_TLS", SlowMlsd
        ):
            gen = collect_from_ftp("ftp.example", "user", "", "/")
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.name, "fast.xml")
                self.assertEqual(first.size, 10)
                self.assertTrue(started.wait(timeout=1))
                release.set()
                rest = [entry.name async for entry in gen]
            finally:
                await gen.aclose()

        self.assertEqual(rest, ["slow.xml"])

    async def test_nlst_fallback_streams_without_size(self):
        """NLST fallback should emit names as lines arrive, without SIZE."""
        started = threading.Event()
        release = threading.Event()
        size_called = []

        class NlstOnly(_FakeMlsdFtp):
            """FTP that rejects MLSD and streams NLST lines."""
            def mlsd(self):
                raise error_perm("MLSD not supported")

            def retrlines(self, cmd, callback):  # pylint: disable=unused-argument
                callback("fast.xml")
                started.set()
                release.wait(timeout=5)
                callback("slow.xml")

            def size(self, name):
                size_called.append(name)
                return 1

        with patch(
            "il_supermarket_scarper.utils.connection.FTP_TLS", NlstOnly
        ):
            gen = collect_from_ftp("ftp.example", "user", "", "/")
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.name, "fast.xml")
                self.assertIsNone(first.size)
                self.assertTrue(started.wait(timeout=1))
                release.set()
                rest = [entry.name async for entry in gen]
            finally:
                await gen.aclose()

        self.assertEqual(rest, ["slow.xml"])
        self.assertEqual(size_called, [])

    async def test_aclose_stops_blocked_listing(self):
        """Closing the generator should not wait for the rest of the listing."""
        entered_slow = threading.Event()

        class StuckMlsd(_FakeMlsdFtp):
            """MLSD that stays blocked until close() is called."""
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._stop = threading.Event()

            def mlsd(self):
                yield ("page1.xml", {"type": "file", "size": "1"})
                entered_slow.set()
                self._stop.wait(timeout=30)
                if self.closed:
                    return
                yield ("page2.xml", {"type": "file", "size": "1"})

            def quit(self):
                self._stop.set()
                super().quit()

            def close(self):
                self._stop.set()
                super().close()

        with patch(
            "il_supermarket_scarper.utils.connection.FTP_TLS", StuckMlsd
        ):
            gen = collect_from_ftp("ftp.example", "user", "", "/")
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.name, "page1.xml")
                self.assertTrue(entered_slow.wait(timeout=1))
            finally:
                await asyncio.wait_for(gen.aclose(), timeout=2)

    async def test_listing_error_propagates(self):
        """A failed FTP login/cwd must not leave the generator blocked."""

        class BoomFtp(_FakeMlsdFtp):
            """FTP that fails on cwd."""
            def cwd(self, path):  # pylint: disable=unused-argument
                raise OSError("cwd failed")

        with patch(
            "il_supermarket_scarper.utils.connection.FTP_TLS", BoomFtp
        ):
            gen = collect_from_ftp("ftp.example", "user", "", "/")
            try:
                with self.assertRaises(OSError):
                    await asyncio.wait_for(anext(gen), timeout=1)
            finally:
                await gen.aclose()
