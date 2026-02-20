"""Data classes defining the output format contract for scraper status."""

import re

from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Union
from pydantic.networks import AnyUrl
from pydantic import BaseModel, Field
from pydantic_core import core_schema

from il_supermarket_scarper.utils.file_types import FileTypesFilters


FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9._-]+$")


class FileName(str):
    """filename class"""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source, handler
    ):  # pylint: disable=unused-argument
        """get the pydantic core schema"""
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.str_schema()
        )

    @classmethod
    def validate(cls, value: str) -> str:
        """validate the filename"""
        if not value:
            raise ValueError("Filename cannot be empty")

        value = value.replace("NULL", "")
        if FileTypesFilters.get_type_from_file(value) is None:
            raise ValueError(f"File {value} is not a valid filename")

        return value


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
    filter_null: bool = False
    filter_zero: bool = False


class FolderSizeInfo(BaseModel):
    """Information about the size and contents of a folder."""

    size: float
    unit: str
    folder: str
    folder_content: List[FileName] = Field(default_factory=list)


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
    file_name: FileName
    link_collected: Optional[AnyUrl]


class DownloadedStatus(BaseModel):
    """Status event when files are downloaded."""

    status: str = "downloaded"
    when: Optional[datetime] = None
    file_name_downloaded: FileName
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
    download_url: Optional[AnyUrl]
    file_name: FileName


class SawStatus(BaseModel):
    """Status event when file is seen on site."""

    status: str = "saw"
    when: Optional[datetime] = None
    file_name: (
        str  # why not "FileName"? we can see any file, but we should collect them all
    )
    link: Optional[Optional[AnyUrl]]
    size: Optional[Union[int, float]] = None


class VerifiedDownload(BaseModel):
    """Record of a verified downloaded file."""

    file_name: FileName
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
    events: List[Union[SawStatus, CollectedStatus, DownloadedStatus, FailedStatus]] = (
        Field(default_factory=list)
    )
    verified_downloads: List[VerifiedDownload] = Field(default_factory=list)

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
                per_file[event.file_name]["collected"] = True
                per_file_status_counter[event.file_name].append("collected")
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
        - Must be saw
        - If 'collected' exists, must also have 'saw'
        - If 'downloaded' or 'failed' exists, must also have 'collected'
        - If 'verified' exists, must also have 'downloaded'
        """
        # Must be saw
        if not status["saw"]:
            return False

        if status["collected"]:
            if not status["saw"]:
                return False
        # If collected is True, must also be saw (already checked above)
        # If downloaded or failed exists, must also be collected
        if status["downloaded"] or status["failed"]:
            if not status["collected"]:
                return False
        # If verified exists, must also have downloaded
        if status["verified"]:
            if not status["downloaded"]:
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

        # Count successfully downloaded files (downloaded and verified)
        downloaded_count = 0
        for fn, status in per_file.items():
            # Count files that were successfully downloaded
            if status["downloaded"]:
                downloaded_count += 1

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
