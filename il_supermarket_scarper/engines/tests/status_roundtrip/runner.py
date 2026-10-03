"""Runs one engine case through ``scrape()`` and loads the status it wrote."""

import json
import os

from il_supermarket_scarper.utils import DiskFileOutput
from il_supermarket_scarper.utils.databases import JsonDataBase
from il_supermarket_scarper.utils.scraping.scraper_status_contract import (
    ScraperStatusOutput,
)

from .cases import EngineCase


class RoundtripRunner:  # pylint: disable=too-few-public-methods
    """Scrape with mocked I/O, then load the written status into the contract."""

    def __init__(self, case: EngineCase, tmp_dir: str):
        self.case = case
        self.root = os.path.join(tmp_dir, case.engine_cls.__name__)
        self.status_dir = os.path.join(self.root, "status")

    async def run(self, download_error=False, process_file_error=None):
        """Return the ``ScraperStatusOutput`` loaded from the real status file."""
        os.makedirs(self.root, exist_ok=True)
        previous_cwd = os.getcwd()
        os.chdir(self.root)  # engines write a cookie file in the CWD
        try:
            with self.case.mocker_cls(download_error=download_error):
                scraper = self._build_scraper()
                if process_file_error is not None:
                    scraper.process_file = self._failing_process_file(
                        scraper, process_file_error
                    )
                async for _ in scraper.scrape():
                    pass
        finally:
            os.chdir(previous_cwd)
        return self._read_status()

    def _build_scraper(self):
        return self.case.scraper_cls(
            file_output=DiskFileOutput(storage_path=os.path.join(self.root, "dump")),
            status_database=JsonDataBase("status", self.status_dir),
        )

    @staticmethod
    def _failing_process_file(scraper, error):
        async def failing(entry):
            # real engines register "collected" before they can fail
            scraper.status.register_collected_file(
                file_name_collected_from_site=entry.name,
                link_collected_from_site=entry.url,
                entry_id=entry.entry_id,
            )
            raise error

        return failing

    def _read_status(self):
        with open(
            os.path.join(self.status_dir, "status.json"), encoding="utf-8"
        ) as status_file:
            return ScraperStatusOutput(**json.load(status_file))
