import os
import traceback

from .logger import Logger
from .status import log_folder_details
from .databases import JsonDataBase
from .status import _now, get_output_folder
from .lock_utils import lock_by_string


class ScraperStatus:
    """A class that abstracts the database interface for scraper status."""

    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    FAILED = "fail"
    ESTIMATED_SIZE = "estimated_size"
    VERIFIED_DOWNLOADS = "verified_downloads"

    def __init__(self, database_name, base_path, folder_name=None) -> None:
        self.database = JsonDataBase(
            database_name, get_output_folder(base_path, folder_name=folder_name)
        )
        self.task_id = _now().strftime("%Y%m%d%H%M%S")
        self.filter_between_itrations = False

    @lock_by_string()
    def on_scraping_start(self, limit, files_types, **additional_info):
        """Report that scraping has started."""
        self._insert_an_update(
            ScraperStatus.STARTED,
            limit=limit,
            files_requested=files_types,
            **additional_info,
        )

    def enable_collection_status(self):
        """enable data collection to status files"""
        self.database.enable_collection_status()

    def enable_aggregation_between_runs(self):
        """allow tracking the downloaded file and don't downloading again if downloaded"""
        self.filter_between_itrations = True

    @lock_by_string()
    def on_collected_details(
        self,
        file_name_collected_from_site,
        links_collected_from_site="",
        **additional_info,
    ):
        """Report that file details have been collected."""
        self._insert_an_update(
            ScraperStatus.COLLECTED,
            file_name_collected_from_site=file_name_collected_from_site,
            links_collected_from_site=links_collected_from_site,
            **additional_info,
        )

    @lock_by_string()
    def on_download_completed(self, **additional_info):
        """Report that the file has been downloaded."""
        self._insert_an_update(ScraperStatus.DOWNLOADED, **additional_info)
        self._add_downloaded_files_to_list(**additional_info)

    async def filter_already_downloaded(
        self, storage_path, files_names_to_scrape, filelist, by_function=lambda x: x
    ):
        """Filter files already existing in long-term memory or previously downloaded."""
        if self.database.is_collection_enabled() and self.filter_between_itrations:
            async for file in filelist:
                if not await self.database.find_document(
                    self.VERIFIED_DOWNLOADS, {"file_name": by_function(file)}
                ) and by_function(file) in files_names_to_scrape:
                    yield file
        else:
            # Fallback: filter according to the disk
            file_list_on_disk = os.listdir(storage_path)
            async for file in filelist:
                if by_function(file) in file_list_on_disk and by_function(file) in files_names_to_scrape:
                    yield file

    def _add_downloaded_files_to_list(self, results, **_):
        """Add downloaded files to the MongoDB collection."""
        if self.database.is_collection_enabled():
            when = _now()

            documents = []
            for res in results:
                if res["extract_succefully"]:
                    documents.append(
                        {"file_name": res["file_name"], "when": when},
                    )
            self.database.insert_documents(self.VERIFIED_DOWNLOADS, documents)

    @lock_by_string()
    def on_scrape_completed(self, folder_name, completed_successfully=True):
        """Report when scraping is completed."""
        self._insert_an_update(
            ScraperStatus.ESTIMATED_SIZE,
            folder_size=log_folder_details(folder_name),
            completed_successfully=completed_successfully,
        )

    @lock_by_string()
    def on_download_fail(self, execption, download_urls=None, file_names=None):
        """report when the scraping in failed"""
        self._insert_an_update(
            ScraperStatus.FAILED,
            execption=str(execption),
            traceback=traceback.format_exc(),
            download_urls=download_urls if download_urls else [],
            file_names=file_names if file_names else [],
        )

    def _insert_an_update(self, status, **additional_info):
        """Insert an update into the MongoDB collection."""
        document = {
            "status": status,
            "when": _now(),
            **additional_info,
        }
        self.database.insert_document(self.task_id, document)
