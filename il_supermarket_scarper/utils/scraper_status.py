import os
import traceback

from .status import log_folder_details
from .databases import JsonDataBase
from .status import _now
from .lock_utils import lock_by_string
from .file_output import FileOutput


class ScraperStatus:
    """A class that abstracts the database interface for scraper status."""

    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    ESTIMATED_SIZE = "estimated_size"
    VERIFIED_DOWNLOADS = "verified_downloads"

    def __init__(self, database_name, base_path, file_output: FileOutput) -> None:
        # Use parent directory of storage path for status files
        status_path = os.path.join(os.path.dirname(file_output.get_storage_path()), "status")
        self.database = JsonDataBase(
            database_name, status_path if status_path else base_path
        )
        self.task_id = _now().strftime("%Y%m%d%H%M%S")
        self.filter_between_itrations = False

    @lock_by_string()
    def on_scraping_start(self, limit, files_types, **additional_info):
        """Report that scraping has started."""
        self._insert_global_status(
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
            "restart_and_retry": results.get("restart_and_retry", False)
        }
        self._insert_event(ScraperStatus.DOWNLOADED, **event_data)
        self._add_downloaded_files_to_list(results)


    async def filter_already_downloaded(
        self, storage_path, files_names_to_scrape, filelist, by_function=lambda x: x
    ):
        """Filter files already existing in long-term memory or previously downloaded."""
        if self.database.is_collection_enabled() and self.filter_between_itrations:
            async for file in filelist:
                if (
                    not await self.database.find_document(
                        self.VERIFIED_DOWNLOADS, {"file_name": by_function(file)}
                    )
                    and by_function(file) in files_names_to_scrape
                ):
                    yield file
        else:
            # Fallback: filter according to the disk
            # Check if storage_path exists first
            if os.path.exists(storage_path):
                file_list_on_disk = os.listdir(storage_path)
            else:
                file_list_on_disk = []

            async for file in filelist:
                # Yield files that are NOT already downloaded (not on disk)
                # OR if files_names_to_scrape is specified, only yield files in that list
                if files_names_to_scrape is not None:
                    # If specific files requested, only yield those that match and aren't downloaded
                    if (
                        by_function(file) in files_names_to_scrape
                        and by_function(file) not in file_list_on_disk
                    ):
                        yield file
                else:
                    # No specific files requested, yield all that aren't already downloaded
                    if by_function(file) not in file_list_on_disk:
                        yield file

    def _add_downloaded_files_to_list(self, results, **_):
        """Add downloaded files to the MongoDB collection."""
        if self.database.is_collection_enabled():
            when = _now() 
            if results["extract_succefully"]:
                self.database.insert_document(self.VERIFIED_DOWNLOADS, {"file_name": results["file_name"], "when": when})

    @lock_by_string()
    def on_scrape_completed(self, folder_name, completed_successfully=True):
        """Report when scraping is completed."""
        self._insert_global_status(
            ScraperStatus.ESTIMATED_SIZE,
            folder_size=log_folder_details(folder_name),
            completed_successfully=completed_successfully,
        )

    @lock_by_string()
    def register_download_fail(self, execption, download_urls=None, file_names=None):
        """report when the scraping in failed"""
        # Map to contract field names
        download_url = download_urls[0] if download_urls else ""
        file_name = file_names[0] if file_names else ""
        
        self._insert_event(
            ScraperStatus.FAILED,
            execption=str(execption),
            traceback=traceback.format_exc(),
            download_url=download_url,
            file_name=file_name,
        )

    def _insert_global_status(self, status, **additional_info):
        """Insert a global status update (started, estimated_size)."""
        document = {
            "status": status,
            "when": _now(),
            **additional_info
        }
        self.database.insert_document("global_status", document)
    
    def _insert_event(self, status, **additional_info):
        """Insert an event update (collected, downloaded, failed)."""
        document = {
            "status": status,
            "when": _now(),
            **additional_info
        }
        self.database.insert_document("events", document)
