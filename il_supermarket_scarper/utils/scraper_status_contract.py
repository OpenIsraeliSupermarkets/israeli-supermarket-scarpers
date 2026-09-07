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

    task_id: str
    status: str = "started"
    system_timestamp: Optional[datetime] = None
    limit: Optional[int] = None
    files_requested: Optional[List[str]] = None
    store_id: Optional[int] = None
    file_name_regex: Optional[str] = None
    when_date: Optional[datetime] = None
    filter_null: bool = False
    filter_zero: bool = False


class FolderSizeInfo(BaseModel):
    """Information about the size and contents of a folder."""

    task_id: str
    size: float
    unit: str
    folder: str
    folder_content: List[FileName] = Field(default_factory=list)


class EstimatedSizeStatus(BaseModel):
    """Status event when scraping is completed."""

    task_id: str
    status: str = "estimated_size"
    system_timestamp: Optional[datetime] = None
    folder_size: Optional[FolderSizeInfo] = None
    completed_successfully: bool = True


# -- Events Status --
class CollectedStatus(BaseModel):
    """Status event when file details are collected."""

    task_id: str
    status: str = "collected"
    system_timestamp: Optional[datetime] = None
    file_name: FileName
    link_collected: Optional[AnyUrl]


class DownloadedStatus(BaseModel):
    """Status event when files are downloaded."""

    task_id: str
    status: str = "downloaded"
    system_timestamp: Optional[datetime] = None
    file_name: FileName
    downloaded_successfully: bool
    extracted_successfully: bool
    error_message: Optional[str] = None
    restart_and_retry: bool = False


class FailedStatus(BaseModel):
    """Status event when scraping fails."""

    task_id: str
    status: str = "failed"
    system_timestamp: Optional[datetime] = None
    execption: str = ""
    traceback: str = ""
    download_url: Optional[AnyUrl]
    file_name: FileName


class SawStatus(BaseModel):
    """Status event when file is seen on site."""

    task_id: str
    status: str = "saw"
    system_timestamp: Optional[datetime] = None
    file_name: (
        str  # why not "FileName"? we can see any file, but we should collect them all
    )
    link: Optional[Optional[AnyUrl]]
    size: Optional[Union[int, float]] = None


class VerifiedDownload(BaseModel):
    """Record of a verified downloaded file."""

    task_id: str
    file_name: FileName
    system_timestamp: datetime


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
        Build per-file status flags.

        Listing sites can emit the same FileNm more than once; that is a
        real saw, not a contract failure. Flags are therefore boolean
        presence, not event counts.

        Returns:
            Maps file name to status flags (saw, collected, downloaded,
            failed, verified).
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

        for event in self.events:
            if isinstance(event, SawStatus):
                per_file[event.file_name]["saw"] = True
            elif isinstance(event, CollectedStatus):
                per_file[event.file_name]["collected"] = True
            elif isinstance(event, DownloadedStatus):
                per_file[event.file_name]["downloaded"] = True
            elif isinstance(event, FailedStatus):
                per_file[event.file_name]["failed"] = True

        for vd in self.verified_downloads:
            per_file[vd.file_name]["verified"] = True

        return per_file

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

    def validate_file_status(self) -> bool:
        """
        Validate that the status file is valid.

        Ensures that for every file name that was actually attempted (downloaded,
        failed, or verified), there is a reasonable 'story' for that file: saw ->
        collected -> (downloaded or failed) -> (verified if downloaded)

        Duplicate events for the same name (e.g. two listing rows) are
        allowed. Only the lifecycle flags are checked.

        Note: Files that were only saw/collected but never attempted (e.g., due to limit
        constraints) are not validated, as they were never intended to be downloaded.
        """
        per_file = self._build_per_file_status_data()

        # Only validate files that were actually attempted (downloaded, failed, or verified)
        # Files that were only saw/collected but never attempted shouldn't be validated
        for status in per_file.values():
            if (status["saw"] or status["collected"]) and not (
                status["downloaded"] or status["failed"] or status["verified"]
            ):
                continue

            if not self._validate_file_lifecycle(status):
                return False

        return True
