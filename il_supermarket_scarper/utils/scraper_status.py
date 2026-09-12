import os
import traceback
from typing import Optional
import uuid
from .status import log_folder_details, _now
from .databases import JsonDataBase, AbstractDataBase
from .file_output import FileOutput
from .scraping_result import ScrapingResult


class ScraperStatus:
    """Journal status events (started/saw/collected/downloaded/failed)."""

    STARTED = "started"
    SAW = "saw"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    ESTIMATED_SIZE = "estimated_size"

    def __init__(
        self,
        database_name,
        status_database: Optional[AbstractDataBase] = None,
        file_output: Optional[FileOutput] = None,
        status_path: Optional[str] = None,
    ) -> None:
        if status_database is None:
            if status_path is None:
                if file_output is None:
                    raise ValueError(
                        "Provide status_database, status_path, or file_output"
                    )
                status_path = os.path.join(
                    os.path.dirname(file_output.get_storage_path()), "status"
                )
            self.database = JsonDataBase(database_name, status_path)
        else:
            self.database = status_database
        self.task_id = None

    def on_scraping_start(self, limit, files_types, **additional_info):
        """Report that scraping has started."""
        self.task_id = str(uuid.uuid4())

        self._insert_global_status(
            ScraperStatus.STARTED,
            limit=limit,
            files_requested=files_types,
            **additional_info,
        )

    def register_saw_file(
        self,
        file_name,
        link,
        size,
        **additional_info,
    ):
        """Report that file details have been collected."""
        self._insert_event(
            ScraperStatus.SAW,
            file_name=file_name,
            link=link,
            size=size,
            **additional_info,
        )

    def register_collected_file(
        self,
        file_name_collected_from_site,
        link_collected_from_site=None,
        **additional_info,
    ):
        """Report that file details have been collected."""

        self._insert_event(
            ScraperStatus.COLLECTED,
            file_name=file_name_collected_from_site,
            link_collected=link_collected_from_site,
            **additional_info,
        )

    def register_downloaded_file(self, results: ScrapingResult):
        """Report that the file has been downloaded (event journal only)."""
        event_data = {
            "file_name": results.file_name,
            "downloaded_successfully": results.downloaded,
            "extracted_successfully": results.extract_succefully,
            "error_message": results.error,
            "restart_and_retry": results.restart_and_retry,
            "content_sha256": results.content_sha256,
            "save_decision": results.save_decision,
        }
        self._insert_event(ScraperStatus.DOWNLOADED, **event_data)

    def on_scrape_completed(
        self, folder_name: str, completed_successfully: bool = True
    ):
        """Report when scraping is completed."""
        self._insert_global_status(
            ScraperStatus.ESTIMATED_SIZE,
            folder_size=log_folder_details(folder_name),
            completed_successfully=completed_successfully,
        )

    def register_download_fail(self, error, file_name: str):
        """report when the scraping in failed"""
        self._insert_event(
            ScraperStatus.FAILED,
            error_message=str(error),
            traceback=traceback.format_exc(),
            file_name=file_name,
        )

    def _insert_global_status(self, status, **additional_info):
        """Insert a global status update (started, estimated_size)."""
        document = {
            "status": status,
            "system_timestamp": _now(),
            "task_id": self.task_id,
            **additional_info,
        }
        self.database.insert_document("global_status", document)

    def _insert_event(self, status, **additional_info):
        """Insert an event update (collected, downloaded, failed)."""
        document = {
            "status": status,
            "system_timestamp": _now(),
            "task_id": self.task_id,
            **additional_info,
        }
        self.database.insert_document("events", document)
