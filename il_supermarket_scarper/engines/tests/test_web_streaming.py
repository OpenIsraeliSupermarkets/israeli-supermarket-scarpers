"""Tests that WebBase yields files from one site before other sites finish listing."""

import asyncio
import tempfile
import unittest
from unittest.mock import MagicMock

from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import DiskFileOutput, DumpFolderNames, FileEntry


class _DummyWeb(WebBase):
    """Minimal WebBase with two listing URLs."""

    def __init__(self, storage_path):
        super().__init__(
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="test",
            url="https://example.test/",
            max_threads=2,
            file_output=DiskFileOutput(storage_path=storage_path),
        )

    async def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        yield {"url": "https://example.test/fast", "method": "GET"}
        yield {"url": "https://example.test/slow", "method": "GET"}


class TestWebStreaming(unittest.IsolatedAsyncioTestCase):
    """Verify listing of multiple sites does not block the first site's files."""

    async def test_yields_fast_site_before_slow_site_finishes(self):
        """First site's files must appear while another listing URL is still in flight."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = _DummyWeb(tmp)
            slow_started = asyncio.Event()
            release_slow = asyncio.Event()

            async def fake_session(**request):
                if "slow" in request["url"]:
                    slow_started.set()
                    await release_slow.wait()
                response = MagicMock()
                response.site = "slow" if "slow" in request["url"] else "fast"
                return response

            scraper.session_with_cookies_by_chain = fake_session
            scraper.get_data_from_page = lambda req_res: [req_res.site]

            async def fake_extract(all_trs):
                for site in all_trs:
                    yield FileEntry(
                        name=f"{site}.xml", url=f"http://x/{site}", size=1
                    )

            scraper.extract_task_from_entry = fake_extract

            gen = scraper.generate_all_files()
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.name, "fast.xml")
                await asyncio.wait_for(slow_started.wait(), timeout=1)
                release_slow.set()
                rest = [entry.name async for entry in gen]
            finally:
                await gen.aclose()

            self.assertEqual(rest, ["slow.xml"])

    async def test_failed_site_does_not_drop_other_site(self):
        """One listing URL error must not hide files already fetched from another."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = _DummyWeb(tmp)

            async def fake_session(**request):
                if "slow" in request["url"]:
                    raise ConnectionError("slow site down")
                response = MagicMock()
                response.site = "fast"
                return response

            scraper.session_with_cookies_by_chain = fake_session
            scraper.get_data_from_page = lambda req_res: [req_res.site]

            async def fake_extract(all_trs):
                for site in all_trs:
                    yield FileEntry(
                        name=f"{site}.xml", url=f"http://x/{site}", size=1
                    )

            scraper.extract_task_from_entry = fake_extract

            names = []
            gen = scraper.generate_all_files()
            try:
                async for entry in gen:
                    names.append(entry.name)
            finally:
                await gen.aclose()

            self.assertEqual(names, ["fast.xml"])
