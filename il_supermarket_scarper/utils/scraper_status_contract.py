"""Data classes defining the output format contract for scraper status."""

from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field

# -- Global Status --


class StartedStatus(BaseModel):
    """Status event when scraping starts."""

    status: str = "started"
    when: Optional[datetime] = None
    limit: Optional[int] = None
    files_requested: Optional[List[str]] = None
    store_id: Optional[int] = None
    files_names_to_scrape: Optional[List[str]] = None
    when_date: Optional[datetime] = None
    filter_nul: bool = False
    filter_zero: bool = False


class FolderSizeInfo(BaseModel):
    """Information about the size and contents of a folder."""

    size: float
    unit: str
    folder: str
    folder_content: List[str] = Field(default_factory=list)


class EstimatedSizeStatus(BaseModel):
    """Status event when scraping is completed."""

    status: str = "estimated_size"
    when: Optional[datetime] = None
    folder_size: Optional[FolderSizeInfo] = None
    completed_successfully: bool = True


# -- Events Status --
class CollectedStatus(BaseModel):
    """Status event when file details are collected."""

    status: str = "collected"
    when: Optional[datetime] = None
    file_names_collected: str
    links_collected: str


class DownloadedStatus(BaseModel):
    """Status event when files are downloaded."""

    status: str = "downloaded"
    when: Optional[datetime] = None
    file_name_downloaded: str
    downloaded_successfully: bool
    extracted_successfully: bool
    error_message: Optional[str] = None
    restart_and_retry: bool = False


class FailedStatus(BaseModel):
    """Status event when scraping fails."""

    status: str = "failed"
    when: Optional[datetime] = None
    execption: str = ""
    traceback: str = ""
    download_url: str
    file_name: str


class SawStatus(BaseModel):
    """Status event when file is seen on site."""

    status: str = "saw"
    when: Optional[datetime] = None
    file_name: str
    link: str
    size: Optional[int] = None


class VerifiedDownload(BaseModel):
    """Record of a verified downloaded file."""

    file_name: str
    when: datetime


# Union type for all possible status events
class ScraperStatusOutput(BaseModel):
    """
    Complete output format for scraper status.

    The main structure is a dictionary where:
    - Keys are task IDs (timestamp strings in format YYYYMMDDHHMMSS)
    - Values are lists of status events
    - Special key "verified_downloads" contains the list of verified downloads
    """

    global_status: List[Union[StartedStatus, EstimatedSizeStatus]] = Field(
        default_factory=list
    )
    events: List[Union[CollectedStatus, DownloadedStatus, FailedStatus, SawStatus]] = (
        Field(default_factory=list)
    )
    verified_downloads: List[VerifiedDownload] = Field(default_factory=list)

    @staticmethod
    def _extract_file_names_from_collected_status(collected_names: str) -> List[str]:
        """Extract and clean file names from a comma-separated string."""
        file_names = []
        if isinstance(collected_names, str):
            for fn in collected_names.split(","):
                fn = fn.strip()
                if fn:
                    file_names.append(fn)
        return file_names

    def _build_per_file_status_data(self):
        """
        Build per-file status records and status counters.

        Returns:
            A tuple of (per_file_dict, per_file_status_counter_dict)
            - per_file_dict: Maps file name to status flags
                (collected, downloaded, failed, verified)
            - per_file_status_counter_dict: Maps file name to list of status types
                for duplicate detection
        """

        per_file = defaultdict(
            lambda: {
                "saw": False,
                "collected": False,
                "downloaded": False,
                "failed": False,
                "verified": False,
            }
        )
        per_file_status_counter = defaultdict(list)

        for event in self.events:
            if isinstance(event, SawStatus):
                fn = event.file_name
                per_file[fn]["saw"] = True
                per_file_status_counter[fn].append("saw")
            elif isinstance(event, CollectedStatus):
                file_names = self._extract_file_names_from_collected_status(
                    event.file_names_collected
                )
                for fn in file_names:
                    per_file[fn]["collected"] = True
                    per_file_status_counter[fn].append("collected")
            elif isinstance(event, DownloadedStatus):
                fn = event.file_name_downloaded
                per_file[fn]["downloaded"] = True
                per_file_status_counter[fn].append("downloaded")
            elif isinstance(event, FailedStatus):
                fn = event.file_name
                per_file[fn]["failed"] = True
                per_file_status_counter[fn].append("failed")

        for vd in self.verified_downloads:
            fn = vd.file_name
            per_file[fn]["verified"] = True
            per_file_status_counter[fn].append("verified")

        return per_file, per_file_status_counter

    @staticmethod
    def _validate_file_lifecycle(status: dict) -> bool:
        """
        Validate a single file's lifecycle.

        Rules:
        - Must be collected
        - Must be either downloaded OR failed
        - If downloaded, must also be verified
        """
        # Must be collected
        if not status["saw"]:
            return False
        if not status["collected"]:
            return False
        # Must be either downloaded OR failed
        if not (status["downloaded"] or status["failed"]):
            return False
        # If downloaded, must be also verified
        if status["downloaded"] and not status["verified"]:
            return False
        return True

    @staticmethod
    def _has_duplicate_statuses(status_counter_list: list) -> bool:
        """Check if a file has duplicate status types."""
        from collections import Counter  # pylint: disable=import-outside-toplevel

        status_counter = Counter(status_counter_list)
        for count in status_counter.values():
            if count > 1:
                return True  # Duplicate status type found
        return False

    def validate_file_status(self) -> bool:
        """
        Validate that the status file is valid.

        Ensures that for every file name that was actually attempted (downloaded,
        failed, or verified), there is a reasonable 'story' for that file: saw ->
        collected -> (downloaded or failed) -> (verified if downloaded)

        Also validates that if a limit was set, only that many files were downloaded.

        Note: Files that were only saw/collected but never attempted (e.g., due to limit
        constraints) are not validated, as they were never intended to be downloaded.
        """
        per_file, per_file_status_counter = self._build_per_file_status_data()

        # Get the limit from StartedStatus if available
        limit = None
        for status_event in self.global_status:
            if isinstance(status_event, StartedStatus):
                limit = status_event.limit
                break

        # Count successfully downloaded files (downloaded and verified)
        downloaded_count = 0
        for fn, status in per_file.items():
            # Count files that were successfully downloaded
            if status["downloaded"]:
                downloaded_count += 1

        # Validate limit if it was set
        if limit is not None and limit > 0:
            if downloaded_count != limit:
                return False

        # Only validate files that were actually attempted (downloaded, failed, or verified)
        # Files that were only saw/collected but never attempted shouldn't be validated
        for fn, status in per_file.items():
            # Skip validation for files that were only saw/collected but never attempted
            if (status["saw"] or status["collected"]) and not (
                status["downloaded"] or status["failed"] or status["verified"]
            ):
                continue

            # Validate files that were actually attempted
            if not self._validate_file_lifecycle(status):
                return False
            if self._has_duplicate_statuses(per_file_status_counter[fn]):
                return False

        return True
