"""Tests that Engine._scrape starts downloads before listing is exhausted."""

import asyncio
import tempfile
import unittest

from il_supermarket_scarper.engines.engine import Engine
from il_supermarket_scarper.utils import DiskFileOutput, DumpFolderNames, ScrapingResult
from il_supermarket_scarper.utils.state import FilterState


class _DummyEngine(Engine):
    """Engine whose listing can block after the first file."""

    def __init__(self, storage_path, release_listing):
        super().__init__(
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="test",
            max_threads=5,
            file_output=DiskFileOutput(storage_path=storage_path),
        )
        self.release_listing = release_listing
        self.downloads_started = []

    async def collect_files_details_from_site(  # pylint: disable=too-many-arguments
        self,
        state,  # pylint: disable=unused-argument
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        file_name_regex=None,
        filter_null=False,
        filter_zero=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):  # pylint: disable=unused-argument
        yield ("http://x/1", "fast.xml")
        await self.release_listing.wait()
        yield ("http://x/2", "slow.xml")

    async def process_file(self, file_details):
        self.downloads_started.append(file_details[1])
        return ScrapingResult(
            file_name=file_details[1],
            downloaded=True,
            extract_succefully=True,
        )


class TestScrapeStreaming(unittest.IsolatedAsyncioTestCase):
    """Verify downloads complete without waiting for remaining listing sites."""

    async def test_first_download_completes_while_later_listing_is_blocked(self):
        """A finished download must be yielded before more links are collected."""
        with tempfile.TemporaryDirectory() as tmp:
            release_listing = asyncio.Event()
            scraper = _DummyEngine(tmp, release_listing)
            state = FilterState()

            gen = scraper._scrape(state)  # pylint: disable=protected-access
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.file_name, "fast.xml")
                self.assertEqual(scraper.downloads_started, ["fast.xml"])
                self.assertFalse(release_listing.is_set())
                release_listing.set()
                second = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(second.file_name, "slow.xml")
            finally:
                await gen.aclose()

    async def test_listing_error_still_yields_started_download(self):
        """A listing failure after the first link must not cancel that download."""

        class _FailAfterFirst(_DummyEngine):
            async def collect_files_details_from_site(  # pylint: disable=too-many-arguments
                self,
                state,  # pylint: disable=unused-argument
                limit=None,
                files_types=None,
                store_id=None,
                when_date=None,
                file_name_regex=None,
                filter_null=False,
                filter_zero=False,
                min_size=None,
                max_size=None,
                random_selection=False,
            ):  # pylint: disable=unused-argument
                yield ("http://x/1", "fast.xml")
                raise RuntimeError("listing died")

            async def process_file(self, file_details):
                await asyncio.sleep(0.05)
                return await super().process_file(file_details)

        with tempfile.TemporaryDirectory() as tmp:
            scraper = _FailAfterFirst(tmp, asyncio.Event())
            state = FilterState()
            gen = scraper._scrape(state)  # pylint: disable=protected-access
            try:
                first = await asyncio.wait_for(anext(gen), timeout=1)
                self.assertEqual(first.file_name, "fast.xml")
                with self.assertRaises(StopAsyncIteration):
                    await anext(gen)
            finally:
                await gen.aclose()

    async def test_failed_download_does_not_drop_sibling(self):
        """One process_file error must still yield other completed downloads."""

        class _FailOne(_DummyEngine):
            async def collect_files_details_from_site(  # pylint: disable=too-many-arguments
                self,
                state,  # pylint: disable=unused-argument
                limit=None,
                files_types=None,
                store_id=None,
                when_date=None,
                file_name_regex=None,
                filter_null=False,
                filter_zero=False,
                min_size=None,
                max_size=None,
                random_selection=False,
            ):  # pylint: disable=unused-argument
                yield ("http://x/1", "good.xml")
                yield ("http://x/2", "bad.xml")

            async def process_file(self, file_details):
                if file_details[1] == "bad.xml":
                    raise RuntimeError("download failed")
                return await super().process_file(file_details)

        with tempfile.TemporaryDirectory() as tmp:
            scraper = _FailOne(tmp, asyncio.Event())
            gen = scraper._scrape(FilterState())  # pylint: disable=protected-access
            try:
                results = [result async for result in gen]
            finally:
                await gen.aclose()

        by_name = {result.file_name: result for result in results}
        self.assertEqual(set(by_name), {"good.xml", "bad.xml"})
        self.assertTrue(by_name["good.xml"].downloaded)
        self.assertFalse(by_name["bad.xml"].downloaded)
