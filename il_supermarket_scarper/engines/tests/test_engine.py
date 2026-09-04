"""Tests for engine-level deduplication and file-name regex filtering."""

import re
import tempfile
import unittest

from il_supermarket_scarper.engines.engine import Engine
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    DiskFileOutput,
    DumpFolderNames,
    FileEntry,
    QueueFileOutput,
    InMemoryQueueHandler,
    get_output_folder,
)


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
        - engine.py: apply_limit → filter_already_downloaded(...)
        - scraper_status.py: filter_already_downloaded checks VERIFIED_DOWNLOADS in DB
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
