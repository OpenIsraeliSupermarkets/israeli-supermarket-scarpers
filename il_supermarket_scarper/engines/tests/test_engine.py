"""Tests for engine-level deduplication logic (filter_already_downloaded)."""
import tempfile
import unittest

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    DumpFolderNames,
    QueueFileOutput,
    InMemoryQueueHandler,
    get_output_folder,
)


class TestEngineDeduplication(unittest.IsolatedAsyncioTestCase):
    """Validate that filter_already_downloaded prevents re-downloading files."""

    async def test_no_duplicate_download(self):
        """Scrape one file, request the same file again, verify it is not re-downloaded.

        Covers:
        - engine.py: apply_limit → filter_already_downloaded(files_names_to_scrape, ...)
        - scraper_status.py: filter_already_downloaded checks VERIFIED_DOWNLOADS in DB
        - scrapper_runner.py: files_names_to_scrape=None means DB is the sole dedup gate
        """
        scraper_enum = ScraperFactory.BAREKET

        with tempfile.TemporaryDirectory() as tmpdirname:
            init_scraper_function = ScraperFactory.get(scraper_enum)
            if init_scraper_function is None:
                self.skipTest(f"{scraper_enum.name} is disabled")

            storage_path = get_output_folder(
                DumpFolderNames[scraper_enum.name].value, tmpdirname
            )
            queue_handler = InMemoryQueueHandler(
                queue_name=f"test_{scraper_enum.name}"
            )
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

            # pass 2: request the same file explicitly — must be filtered by DB
            second_results = []
            async for result in scraper.scrape(
                files_names_to_scrape=[first_file],
                filter_null=False,
                filter_zero=False,
            ):
                second_results.append(result)

            self.assertEqual(
                len(second_results),
                0,
                f"{first_file} should not be downloaded again but got {second_results}",
            )
