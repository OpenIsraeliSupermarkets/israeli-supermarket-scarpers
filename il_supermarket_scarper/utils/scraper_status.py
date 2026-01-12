import os
import traceback

from .status import log_folder_details
from .databases import JsonDataBase, AbstractDataBase
from .status import _now
from .lock_utils import lock_by_string
from .file_output import FileOutput
from typing import Optional


class ScraperStatus:
    """A class that abstracts the database interface for scraper status."""

    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    ESTIMATED_SIZE = "estimated_size"
    VERIFIED_DOWNLOADS = "verified_downloads"

    def __init__(self, database_name, status_database: Optional[AbstractDataBase] = None, file_output: Optional[FileOutput] = None) -> None:
        # Use provided database or create default JsonDataBase
        if status_database is None:
            # Default: use JSON database in status subdirectory of file output path
            status_path = os.path.join(
                os.path.dirname(file_output.get_storage_path()), "status"
            )
            self.database = JsonDataBase(database_name, status_path)
        else:
            self.database = status_database
        self.task_id = _now().strftime("%Y%m%d%H%M%S")

    @lock_by_string()
    def on_scraping_start(self, limit, files_types, **additional_info):
        """Report that scraping has started."""
        self._insert_global_status(
            ScraperStatus.STARTED,
            limit=limit,
            files_requested=files_types,
            **additional_info,
        )

    @lock_by_string()
    def register_collected_file(
        self,
        file_name_collected_from_site,
        links_collected_from_site="",
        **additional_info,
    ):
        """Report that file details have been collected."""
        # Convert to comma-separated strings to match contract
        if isinstance(file_name_collected_from_site, list):
            file_names_str = ", ".join(file_name_collected_from_site)
        else:
            file_names_str = file_name_collected_from_site

        if isinstance(links_collected_from_site, list):
            links_str = ", ".join(links_collected_from_site)
        else:
            links_str = links_collected_from_site

        self._insert_event(
            ScraperStatus.COLLECTED,
            file_names_collected=file_names_str,
            links_collected=links_str,
            **additional_info,
        )

    @lock_by_string()
    def register_downloaded_file(self, results):
        """Report that the file has been downloaded."""
        # Map results to contract field names
        event_data = {
            "file_name_downloaded": results.get("file_name", ""),
            "downloaded_successfully": results.get("downloaded", False),
            "extracted_successfully": results.get("extract_succefully", False),
            "error_message": results.get("error"),
            "restart_and_retry": results.get("restart_and_retry", False),
        }
        self._insert_event(ScraperStatus.DOWNLOADED, **event_data)
        self._add_downloaded_files_to_list(results)

    async def filter_already_downloaded(
        self, files_names_to_scrape, filelist, by_function=lambda x: x
    ):
        """Filter files already existing in long-term memory or previously downloaded."""
        async for file in filelist:
            already_downloaded = self.database.already_downloaded(
                self.VERIFIED_DOWNLOADS, {"file_name": by_function(file)}
            )
            required_file = files_names_to_scrape is None or by_function(file) in files_names_to_scrape
            if not already_downloaded and required_file:
                yield file

    def _add_downloaded_files_to_list(self, results, **_):
        """Add downloaded files to the database collection."""
        if results["extract_succefully"]:
            self.database.insert_document(
                self.VERIFIED_DOWNLOADS,
                {"file_name": results["file_name"], "when": _now()},
            )

    @lock_by_string()
    def on_scrape_completed(self, folder_name, completed_successfully=True):
        """Report when scraping is completed."""
        self._insert_global_status(
            ScraperStatus.ESTIMATED_SIZE,
            folder_size=log_folder_details(folder_name),
            completed_successfully=completed_successfully,
        )

    @lock_by_string()
    def register_download_fail(self, error, file_name: str):
        """report when the scraping in failed"""
        # Map to contract field names
        self._insert_event(
            ScraperStatus.FAILED,
            error_message=str(error),
            traceback=traceback.format_exc(),
            file_name=file_name,
        )

    def _insert_global_status(self, status, **additional_info):
        """Insert a global status update (started, estimated_size)."""
        document = {"status": status, "when": _now(), **additional_info}
        self.database.insert_document("global_status", document)

    def _insert_event(self, status, **additional_info):
        """Insert an event update (collected, downloaded, failed)."""
        document = {"status": status, "when": _now(), **additional_info}
        self.database.insert_document("events", document)
