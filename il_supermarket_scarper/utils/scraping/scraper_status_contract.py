"""Data classes defining the output format contract for scraper status."""

import re

from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Union
from pydantic.networks import AnyUrl
from pydantic import BaseModel, Field
from pydantic_core import core_schema

from il_supermarket_scarper.utils.files.file_types import FileTypesFilters
from il_supermarket_scarper.utils.files.save_policy import SaveDecision


FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9._-]+$")
ALLOWED_SAVE_DECISIONS = {decision.value for decision in SaveDecision}


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
        if "/" in value or "\\" in value:
            raise ValueError("Filename must not contain path separators")
        if not FILENAME_REGEX.match(value):
            raise ValueError("Filename contains invalid characters")
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

    @staticmethod
    def _append_timestamp(status: dict, kind: str, when) -> None:
        """Record an event timestamp when present."""
        if when is not None:
            status["timestamps"][kind].append(when)

    def _build_per_file_status_data(self):
        """
        Build per-story status flags and event counts.

        Prefer ``entry_id`` so the same FileNm listed twice is validated as
        separate download stories. Fall back to file name for older status
        rows that lack ``entry_id``.

        For ``id:`` stories, each event kind may appear at most once.
        For ``name:`` stories, duplicate ``saw`` / collected / downloaded /
        verified is allowed (legacy duplicate listings); ``failed`` is not.

        Returns:
            Maps story key to status flags, counts, timestamps, and download
            / verified rows used by extra checks.
        """

        per_file = defaultdict(
            lambda: {
                "saw": False,
                "collected": False,
                "downloaded": False,
                "failed": False,
                "verified": False,
                "extracted_successfully": False,
                "keyed_by_entry_id": False,
                "file_name": None,
                "counts": defaultdict(int),
                "timestamps": defaultdict(list),
                "downloads": [],
                "verified_rows": [],
            }
        )

        for event in self.events:
            key = self._story_key(event)
            bucket = per_file[key]
            bucket["keyed_by_entry_id"] = key.startswith("id:")
            bucket["file_name"] = event.file_name
            if isinstance(event, SawStatus):
                bucket["saw"] = True
                bucket["counts"]["saw"] += 1
                self._append_timestamp(bucket, "saw", event.system_timestamp)
            elif isinstance(event, CollectedStatus):
                bucket["collected"] = True
                bucket["counts"]["collected"] += 1
                self._append_timestamp(bucket, "collected", event.system_timestamp)
            elif isinstance(event, DownloadedStatus):
                bucket["downloaded"] = True
                bucket["counts"]["downloaded"] += 1
                bucket["downloads"].append(event)
                self._append_timestamp(bucket, "downloaded", event.system_timestamp)
                if event.extracted_successfully:
                    bucket["extracted_successfully"] = True
            elif isinstance(event, FailedStatus):
                bucket["failed"] = True
                bucket["counts"]["failed"] += 1
                self._append_timestamp(bucket, "failed", event.system_timestamp)

        for vd in self.verified_downloads:
            key = self._story_key(vd)
            bucket = per_file[key]
            bucket["keyed_by_entry_id"] = key.startswith("id:")
            bucket["file_name"] = vd.file_name
            bucket["verified"] = True
            bucket["counts"]["verified"] += 1
            bucket["verified_rows"].append(vd)
            self._append_timestamp(bucket, "verified", vd.system_timestamp)

        return per_file

    def _started_limit(self):
        """Return the scrape limit from started status, or None."""
        for event in self.global_status:
            if isinstance(event, StartedStatus):
                return event.limit
        return None

    def _has_started(self) -> bool:
        """True when at least one started global status exists."""
        return any(isinstance(event, StartedStatus) for event in self.global_status)

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
        if not status["saw"]:
            return False

        if status["collected"] and not status["saw"]:
            return False
        if status["downloaded"] or status["failed"]:
            if not status["collected"]:
                return False
        if status["verified"] and not status["downloaded"]:
            return False
        if status["extracted_successfully"] and not status["verified"]:
            return False
        return True

    @staticmethod
    def _has_duplicate_attempt_events(status: dict) -> bool:
        """
        Detect duplicate events for one story.

        ``id:`` stories: every kind at most once.
        ``name:`` stories: only ``failed`` must be unique (legacy listings).
        """
        if status["keyed_by_entry_id"]:
            for kind in ("saw", "collected", "downloaded", "failed", "verified"):
                if status["counts"][kind] > 1:
                    return True
            return False
        return status["counts"]["failed"] > 1

    @staticmethod
    def _validate_event_order(status: dict) -> bool:
        """For ``id:`` stories, timestamps must follow saw→collected→attempt→verified."""
        if not status["keyed_by_entry_id"]:
            return True

        stamps = status["timestamps"]

        def _max_of(kind):
            values = stamps.get(kind) or []
            return max(values) if values else None

        def _min_of(kind):
            values = stamps.get(kind) or []
            return min(values) if values else None

        stages = []
        for kind in ("saw", "collected"):
            when = _max_of(kind)
            if when is not None:
                stages.append(when)

        attempt_times = []
        for kind in ("downloaded", "failed"):
            when = _min_of(kind)
            if when is not None:
                attempt_times.append(when)
        if attempt_times:
            stages.append(min(attempt_times))

        verified_when = _min_of("verified")
        if verified_when is not None:
            stages.append(verified_when)

        return all(left <= right for left, right in zip(stages, stages[1:]))

    @staticmethod
    def _validate_save_decision(value: Optional[str]) -> bool:
        """Allow missing save_decision; otherwise require a known enum value."""
        if value is None:
            return True
        return value in ALLOWED_SAVE_DECISIONS

    @staticmethod
    def _validate_download_outcomes(status: dict) -> bool:
        """Failed downloads need an error; save_decision must be known."""
        for download in status["downloads"]:
            if not download.downloaded_successfully and not download.error_message:
                return False
            if not ScraperStatusOutput._validate_save_decision(download.save_decision):
                return False
        return True

    @staticmethod
    def _validate_verified_rows(status: dict) -> bool:
        """Verified rows need a listing_hash and a known save_decision when set."""
        download_has_digest = any(
            download.content_sha256 for download in status["downloads"]
        )
        for row in status["verified_rows"]:
            if not row.listing_hash:
                return False
            if not ScraperStatusOutput._validate_save_decision(row.save_decision):
                return False
            if (
                status["keyed_by_entry_id"]
                and status["extracted_successfully"]
                and download_has_digest
                and not row.content_sha256
            ):
                return False
        return True

    def _validate_key_hygiene(self, per_file: dict) -> bool:
        """Do not mix entry_id and name-only events for the same FileNm."""
        names_with_id = set()
        names_without_id = set()
        for key, status in per_file.items():
            file_name = status["file_name"]
            if not file_name:
                continue
            if key.startswith("id:"):
                names_with_id.add(file_name)
            else:
                names_without_id.add(file_name)
        return names_with_id.isdisjoint(names_without_id)

    def validate_file_status(self) -> bool:
        """
        Validate that the status file is valid.

        For every download story that was actually attempted (downloaded,
        failed, or verified), keyed by ``entry_id`` when present else
        file name:

        - Lifecycle: saw -> collected -> (downloaded or failed) ->
          (verified if extract succeeded)
        - ``id:`` stories: each event kind at most once; timestamps ordered
        - ``name:`` stories: duplicate saw/collected/downloaded/verified ok;
          duplicate failed is not
        - Download outcomes / save_decision / verified listing_hash checks
        - No mixing of entry_id and name-only keys for the same FileNm
        - Any events or verified rows require a started global status
        - If a started ``limit`` is set, downloaded stories must not exceed it

        Note: Stories that were only saw/collected but never attempted (e.g., due to limit
        constraints) are not validated, as they were never intended to be downloaded.
        """
        if (self.events or self.verified_downloads) and not self._has_started():
            return False

        per_file = self._build_per_file_status_data()
        if not self._validate_key_hygiene(per_file):
            return False

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
            if not self._validate_event_order(status):
                return False
            if not self._validate_download_outcomes(status):
                return False
            if not self._validate_verified_rows(status):
                return False

        limit = self._started_limit()
        if limit is not None and downloaded_count > limit:
            return False

        return True
