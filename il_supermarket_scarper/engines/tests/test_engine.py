"""Tests for engine-level deduplication and file-name regex filtering."""

import re
import tempfile
import unittest
from datetime import datetime

from il_supermarket_scarper.engines.engine import Engine
from il_supermarket_scarper.scrappers.wolt import Wolt
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    DiskFileOutput,
    DumpFolderNames,
    FileEntry,
    FileTypesFilters,
    QueueFileOutput,
    InMemoryQueueHandler,
    get_output_folder,
)
from il_supermarket_scarper.utils.databases import JsonDataBase
from il_supermarket_scarper.utils.state import FilterState
from il_supermarket_scarper.utils.verified_downloads import VerifiedDownloads


class TestEngineDeduplication(unittest.IsolatedAsyncioTestCase):
    """Validate that filter_already_downloaded prevents re-downloading files."""

    async def test_file_name_regex_filters_names(self):
        """Only file names matching the regex are yielded."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            scraper_class = ScraperFactory.get(ScraperFactory.BAREKET)
            if scraper_class is None:
                self.skipTest("BAREKET is disabled")
            scraper = scraper_class(file_output=DiskFileOutput(tmpdirname))

            async def files():
                yield FileEntry(name="PriceFull7290-001.xml", url="http://x/1", size=1)
                yield FileEntry(name="Promo7290-001.xml", url="http://x/2", size=1)

            kept = []
            async for entry in scraper.filter_by_file_name_regex(
                files(), r"PriceFull", by_function=lambda file: file.name
            ):
                kept.append(entry.name)

            self.assertEqual(kept, ["PriceFull7290-001.xml"])

    def test_invalid_file_name_regex_raises(self):
        """Invalid regex strings fail validation before scraping."""
        with self.assertRaises(ValueError):
            Engine._compile_file_name_regex(  # pylint: disable=protected-access
                "[unterminated"
            )

    async def test_no_duplicate_download(self):
        """Scrape one file, request the same file again, verify it is not re-downloaded.

        Covers:
        - engine.py: apply_limit → verified.filter_already_downloaded(...)
        - verified_downloads.py: filter checks listing_hash in verified_downloads
        - scrapper_runner.py: file_name_regex is forwarded into scrape()
        """
        scraper_enum = ScraperFactory.BAREKET

        with tempfile.TemporaryDirectory() as tmpdirname:
            init_scraper_function = ScraperFactory.get(scraper_enum)
            if init_scraper_function is None:
                self.skipTest(f"{scraper_enum.name} is disabled")

            storage_path = get_output_folder(
                DumpFolderNames[scraper_enum.name].value, tmpdirname
            )
            queue_handler = InMemoryQueueHandler(queue_name=f"test_{scraper_enum.name}")
            scraper = init_scraper_function(
                file_output=QueueFileOutput(queue_handler, storage_path)
            )

            # pass 1: scrape one file
            first_file = None
            async for result in scraper.scrape(
                limit=1,
                filter_null=False,
                filter_zero=False,
                min_size=1,
                max_size=10_000_000,
            ):
                if result.extract_succefully:
                    first_file = result.file_name
                    break

            if first_file is None:
                self.skipTest(f"{scraper_enum.name} returned no downloadable files")

            # pass 2: request the same file by regex — must be filtered by DB
            second_results = []
            async for result in scraper.scrape(
                file_name_regex=re.escape(first_file),
                filter_null=False,
                filter_zero=False,
            ):
                second_results.append(result)

            self.assertEqual(
                len(second_results),
                0,
                f"{first_file} should not be downloaded again but got {second_results}",
            )


class TestApplyLimitAfterFilters(unittest.IsolatedAsyncioTestCase):
    """Limit must run after type/date filters, not before."""

    def _wolt(self, tmp):
        """Wolt with status DB inside ``tmp`` so tests do not share verified names."""
        return Wolt(
            file_output=DiskFileOutput(storage_path=tmp),
            status_database=JsonDataBase("wolt_apply_limit", tmp),
        )

    async def test_limit_does_not_consume_quota_on_wrong_date(self):
        """Older type-matching files must not burn limit before when_date."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = self._wolt(tmp)

            async def listed():
                for name in (
                    "PromoFull7290058249350-000-001-20260904-000001",
                    "PromoFull7290058249350-000-002-20260905-000001",
                    "PromoFull7290058249350-000-003-20260906-000001",
                    "PromoFull7290058249350-000-004-20260907-000001",
                    "PromoFull7290058249350-000-005-20260907-000002",
                    "PromoFull7290058249350-000-006-20260907-000003",
                    "Price7290058249350-000-007-20260907-000001",
                ):
                    yield FileEntry(name=name, url=f"http://example.test/{name}", size=1)

            state = FilterState()
            names = []
            async for entry in scraper.apply_limit(
                state,
                listed(),
                limit=3,
                files_types=[FileTypesFilters.PROMO_FULL_FILE.name],
                when_date=datetime(2026, 9, 7),
            ):
                names.append(entry.name)

            self.assertEqual(
                names,
                [
                    "PromoFull7290058249350-000-004-20260907-000001",
                    "PromoFull7290058249350-000-005-20260907-000002",
                    "PromoFull7290058249350-000-006-20260907-000003",
                ],
            )
            self.assertEqual(state.file_pass_limit, 3)

    async def test_duplicate_listing_names_are_kept(self):
        """The same FileNm listed twice must both pass apply_limit."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = self._wolt(tmp)
            name = "PromoFull7290058249350-000-004-20260907-000001"

            async def listed():
                yield FileEntry(name=name, url="http://example.test/a", size=1)
                yield FileEntry(name=name, url="http://example.test/b", size=1)

            state = FilterState()
            kept = []
            async for entry in scraper.apply_limit(state, listed(), limit=2):
                kept.append((entry.name, entry.url))

            self.assertEqual(
                kept,
                [
                    (name, "http://example.test/a"),
                    (name, "http://example.test/b"),
                ],
            )
            self.assertEqual(state.file_pass_limit, 2)

    async def test_verified_listing_hash_skips_only_that_listing(self):
        """Same FileNm with a different url/size still downloads."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = self._wolt(tmp)
            name = "PromoFull7290058249350-000-004-20260907-000001"
            first = FileEntry(name=name, url="http://example.test/a", size=1)
            second = FileEntry(name=name, url="http://example.test/b", size=1)
            scraper.status.database.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": name,
                    "listing_hash": first.listing_hash(),
                    "task_id": "previous",
                },
            )

            async def listed():
                yield first
                yield second

            state = FilterState()
            kept = []
            async for entry in scraper.apply_limit(state, listed(), limit=2):
                kept.append((entry.name, entry.url))

            self.assertEqual(kept, [(name, "http://example.test/b")])

    async def test_identical_verified_listing_is_skipped(self):
        """The same FileEntry hash is not downloaded again."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = self._wolt(tmp)
            entry = FileEntry(
                name="PromoFull7290058249350-000-004-20260907-000001",
                url="http://example.test/a",
                size=1,
            )
            scraper.status.database.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": entry.name,
                    "listing_hash": entry.listing_hash(),
                    "task_id": "previous",
                },
            )

            async def listed():
                yield entry
                yield entry

            state = FilterState()
            kept = []
            async for item in scraper.apply_limit(state, listed(), limit=2):
                kept.append(item)

            self.assertEqual(kept, [])

    async def test_identical_listings_in_one_scrape_are_deduped(self):
        """Same name+url+size is listed once; a second copy is not downloaded."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = self._wolt(tmp)
            entry = FileEntry(
                name="PromoFull7290058249350-000-004-20260907-000001",
                url="http://example.test/a",
                size=1,
            )

            async def listed():
                yield entry
                yield entry

            state = FilterState()
            kept = []
            async for item in scraper.apply_limit(state, listed(), limit=2):
                kept.append(item)

            self.assertEqual(kept, [entry])
            self.assertEqual(state.file_pass_limit, 1)

    async def test_verified_without_listing_hash_does_not_skip(self):
        """After a DB clean, name-only rows must not block a new listing hash."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = self._wolt(tmp)
            name = "PromoFull7290058249350-000-004-20260907-000001"
            scraper.status.database.insert_document(
                VerifiedDownloads.COLLECTION,
                {
                    "file_name": name,
                    "task_id": "previous",
                },
            )

            async def listed():
                yield FileEntry(name=name, url="http://example.test/a", size=1)
                yield FileEntry(name=name, url="http://example.test/b", size=2)

            state = FilterState()
            kept = []
            async for item in scraper.apply_limit(state, listed(), limit=2):
                kept.append((item.name, item.url))

            self.assertEqual(
                kept,
                [
                    (name, "http://example.test/a"),
                    (name, "http://example.test/b"),
                ],
            )
