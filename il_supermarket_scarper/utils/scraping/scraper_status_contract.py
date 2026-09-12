"""Data classes defining the output format contract for scraper status."""

import re

from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Union
from pydantic.networks import AnyUrl
from pydantic import BaseModel, Field
from pydantic_core import core_schema

from il_supermarket_scarper.utils.files.file_types import FileTypesFilters


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
    entry_id: Optional[str] = None


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
    content_sha256: Optional[str] = None
    save_decision: Optional[str] = None
    entry_id: Optional[str] = None


class FailedStatus(BaseModel):
    """Status event when scraping fails."""

    task_id: str
    status: str = "failed"
    system_timestamp: Optional[datetime] = None
    execption: str = ""
    traceback: str = ""
    download_url: Optional[AnyUrl]
    file_name: FileName
    entry_id: Optional[str] = None


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
    entry_id: Optional[str] = None


class VerifiedDownload(BaseModel):
    """Record of a verified downloaded file."""

    task_id: str
    file_name: FileName
    system_timestamp: datetime
    content_sha256: Optional[str] = None
    save_decision: Optional[str] = None
    listing_hash: str
    published_at: Optional[str] = None
    entry_id: Optional[str] = None


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

    @staticmethod
    def _story_key(event) -> str:
        """Key one download story: prefer entry_id, else file name."""
        entry_id = getattr(event, "entry_id", None)
        if entry_id:
            return f"id:{entry_id}"
        return f"name:{event.file_name}"

    def _build_per_file_status_data(self):
        """
        Build per-story status flags and event counts.

        Prefer ``entry_id`` so the same FileNm listed twice is validated as
        separate download stories. Fall back to file name for older status
        rows that lack ``entry_id``.

        Listing sites can emit the same FileNm more than once; that is a
        real listing, not a contract failure. ``saw``, ``collected``,
        ``downloaded``, and ``verified`` may appear more than once for
        that name when keyed only by name. ``failed`` should not repeat
        for the same story key.

        Returns:
            Maps story key to status flags, counts, and whether a
            download extracted successfully.
        """

        per_file = defaultdict(
            lambda: {
                "saw": False,
                "collected": False,
                "downloaded": False,
                "failed": False,
                "verified": False,
                "extracted_successfully": False,
                "counts": defaultdict(int),
            }
        )

        for event in self.events:
            key = self._story_key(event)
            if isinstance(event, SawStatus):
                per_file[key]["saw"] = True
                per_file[key]["counts"]["saw"] += 1
            elif isinstance(event, CollectedStatus):
                per_file[key]["collected"] = True
                per_file[key]["counts"]["collected"] += 1
            elif isinstance(event, DownloadedStatus):
                per_file[key]["downloaded"] = True
                per_file[key]["counts"]["downloaded"] += 1
                if event.extracted_successfully:
                    per_file[key]["extracted_successfully"] = True
            elif isinstance(event, FailedStatus):
                per_file[key]["failed"] = True
                per_file[key]["counts"]["failed"] += 1

        for vd in self.verified_downloads:
            key = self._story_key(vd)
            per_file[key]["verified"] = True
            per_file[key]["counts"]["verified"] += 1

        return per_file

    def _started_limit(self):
        """Return the scrape limit from started status, or None."""
        for event in self.global_status:
            if isinstance(event, StartedStatus):
                return event.limit
        return None

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
        # A successful extract must be recorded as verified.
        if status["extracted_successfully"] and not status["verified"]:
            return False
        return True

    @staticmethod
    def _has_duplicate_attempt_events(status: dict) -> bool:
        """A file may be collected/downloaded twice; it must not fail twice."""
        return status["counts"]["failed"] > 1

    def validate_file_status(self) -> bool:
        """
        Validate that the status file is valid.

        For every download story that was actually attempted (downloaded,
        failed, or verified), keyed by ``entry_id`` when present else
        file name:

        - Lifecycle: saw -> collected -> (downloaded or failed) ->
          (verified if extract succeeded)
        - Duplicate ``saw`` / collected / downloaded / verified is allowed
          for the same file name when stories lack ``entry_id`` (listing
          listed the same dump twice)
        - Duplicate ``failed`` for the same story key is not
        - If a started ``limit`` is set, downloaded stories must not
          exceed it

        Note: Stories that were only saw/collected but never attempted (e.g., due to limit
        constraints) are not validated, as they were never intended to be downloaded.
        """
        per_file = self._build_per_file_status_data()
        downloaded_count = 0

        for status in per_file.values():
            if status["downloaded"]:
                downloaded_count += 1
            if (status["saw"] or status["collected"]) and not (
                status["downloaded"] or status["failed"] or status["verified"]
            ):
                continue

            if not self._validate_file_lifecycle(status):
                return False
            if self._has_duplicate_attempt_events(status):
                return False

        limit = self._started_limit()
        if limit is not None and downloaded_count > limit:
            return False

        return True
