"""Tests that MultiPageWeb yields listing results before all pages finish."""

import asyncio
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

from il_supermarket_scarper.engines.multipage_web import MultiPageWeb
from il_supermarket_scarper.utils import DiskFileOutput, DumpFolderNames, FileEntry
from il_supermarket_scarper.utils.state import FilterState


class _DummyMultiPage(MultiPageWeb):
    """Minimal MultiPageWeb for unit tests."""

    def __init__(self, storage_path):
        super().__init__(
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="test",
            url="https://example.test/",
            max_threads=2,
            file_output=DiskFileOutput(storage_path=storage_path),
        )

    def build_params(self, files_types=None, store_id=None, when_date=None):
        return ["?cat=1"]


class TestMultiPageStreaming(unittest.IsolatedAsyncioTestCase):
    """Verify listing streams page-by-page instead of waiting for gather."""

    async def test_yields_before_slower_pages_finish(self):
        """Fast page results must appear while a slow page is still running."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = _DummyMultiPage(tmp)
            scraper.session_with_cookies_by_chain = AsyncMock(
                return_value=MagicMock(content=b"<html></html>")
            )
            scraper.get_number_of_pages = MagicMock(return_value=3)

            started = asyncio.Event()
            release_slow = asyncio.Event()
            yielded_names = []

            async def fake_process_links(  # pylint: disable=unused-argument
                state,
                request,
                limit=None,
                files_types=None,
                store_id=None,
                when_date=None,
                random_selection=False,
            ):
                url = request["url"]
                if "page=1" in url:
                    yield FileEntry(name="fast-1.xml", url="http://x/1", size=1)
                elif "page=2" in url:
                    started.set()
                    await release_slow.wait()
                    yield FileEntry(name="slow-2.xml", url="http://x/2", size=1)
                else:
                    yield FileEntry(name="fast-3.xml", url="http://x/3", size=1)

            scraper.process_links_before_download = fake_process_links

            gen = scraper.generate_all_files(limit=10)
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                yielded_names.append(first.name)

                # Slow page should have started while we already have a result.
                await asyncio.wait_for(started.wait(), timeout=1)
                self.assertIn(first.name, {"fast-1.xml", "fast-3.xml"})

                release_slow.set()
                async for entry in gen:
                    yielded_names.append(entry.name)
            finally:
                await gen.aclose()

            self.assertEqual(
                set(yielded_names), {"fast-1.xml", "slow-2.xml", "fast-3.xml"}
            )

    async def test_aclose_cancels_pending_pages(self):
        """Closing the generator should cancel unfinished page tasks."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = _DummyMultiPage(tmp)
            scraper.session_with_cookies_by_chain = AsyncMock(
                return_value=MagicMock(content=b"<html></html>")
            )
            scraper.get_number_of_pages = MagicMock(return_value=2)

            slow_entered = asyncio.Event()
            slow_cancelled = asyncio.Event()

            async def fake_process_links(  # pylint: disable=unused-argument
                state,
                request,
                limit=None,
                files_types=None,
                store_id=None,
                when_date=None,
                random_selection=False,
            ):
                url = request["url"]
                if "page=1" in url:
                    yield FileEntry(name="page1.xml", url="http://x/1", size=1)
                else:
                    slow_entered.set()
                    try:
                        await asyncio.sleep(60)
                    except asyncio.CancelledError:
                        slow_cancelled.set()
                        raise
                    yield FileEntry(name="page2.xml", url="http://x/2", size=1)

            scraper.process_links_before_download = fake_process_links

            gen = scraper.generate_all_files()
            try:
                first = await anext(gen)
                self.assertEqual(first.name, "page1.xml")
                await asyncio.wait_for(slow_entered.wait(), timeout=1)
            finally:
                await gen.aclose()

            await asyncio.wait_for(slow_cancelled.wait(), timeout=1)
            self.assertTrue(slow_cancelled.is_set())

    async def test_limit_stops_scheduling_more_pages(self):
        """After enough files, remaining queued pages should not be fetched."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = _DummyMultiPage(tmp)
            scraper.max_threads = 1
            scraper.session_with_cookies_by_chain = AsyncMock(
                return_value=MagicMock(content=b"<html></html>")
            )
            scraper.get_number_of_pages = MagicMock(return_value=5)

            fetched_pages = []

            async def fake_process_links(  # pylint: disable=unused-argument
                state,
                request,
                limit=None,
                files_types=None,
                store_id=None,
                when_date=None,
                random_selection=False,
            ):
                url = request["url"]
                page_num = url.rsplit("page=", 1)[-1]
                fetched_pages.append(page_num)
                yield FileEntry(
                    name=f"file-{page_num}.xml", url=f"http://x/{page_num}", size=1
                )

            scraper.process_links_before_download = fake_process_links

            # limit=1 through the full collect pipeline should aclose listing
            # before later pages are scheduled (max_in_flight=1).
            results = []
            gen = scraper.collect_files_details_from_site(
                state=FilterState(),
                limit=1,
            )
            try:
                async for item in gen:
                    results.append(item)
            finally:
                await gen.aclose()

            self.assertEqual(len(results), 1)
            self.assertLessEqual(len(fetched_pages), 2)

    async def test_second_listing_root_does_not_block_first(self):
        """Files from a fast listing root must yield while another root is still loading."""

        class _TwoRootDummy(_DummyMultiPage):
            def build_params(self, files_types=None, store_id=None, when_date=None):
                return ["?cat=1", "?cat=2"]

        with tempfile.TemporaryDirectory() as tmp:
            scraper = _TwoRootDummy(tmp)
            slow_root_started = asyncio.Event()
            release_slow_root = asyncio.Event()

            async def fake_session(**request):
                if "cat=2" in request["url"]:
                    slow_root_started.set()
                    await release_slow_root.wait()
                return MagicMock(content=b"<html></html>")

            scraper.session_with_cookies_by_chain = fake_session
            scraper.get_number_of_pages = MagicMock(return_value=None)

            async def fake_process_links(  # pylint: disable=unused-argument
                state,
                request,
                limit=None,
                files_types=None,
                store_id=None,
                when_date=None,
                random_selection=False,
            ):
                cat = "2" if "cat=2" in request["url"] else "1"
                yield FileEntry(
                    name=f"cat-{cat}.xml", url=f"http://x/{cat}", size=1
                )

            scraper.process_links_before_download = fake_process_links

            gen = scraper.generate_all_files()
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.name, "cat-1.xml")
                await asyncio.wait_for(slow_root_started.wait(), timeout=1)
                release_slow_root.set()
                rest = [entry.name async for entry in gen]
            finally:
                await gen.aclose()

            self.assertEqual(set(rest), {"cat-2.xml"})
