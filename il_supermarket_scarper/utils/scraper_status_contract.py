"""Data classes defining the output format contract for scraper status."""

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
    events: List[Union[CollectedStatus, DownloadedStatus, FailedStatus]] = Field(
        default_factory=list
    )
    verified_downloads: List[VerifiedDownload] = Field(default_factory=list)

    def validate_file_status(self) -> bool:  # pylint: disable=too-many-branches
        """
        Validate that the status file is valid.

        Ensures that for every file name appearing in any event (collect, download,
        fail, verified), there is a reasonable 'story' for that file: collected ->
        (downloaded or failed) -> (verified or failed)
        """
        from collections import (
            defaultdict,
            Counter,
        )  # pylint: disable=import-outside-toplevel

        # Gather all unique file names across all event types
        file_names_set = set()

        for event in self.events:
            if isinstance(event, CollectedStatus):
                collected_names = event.file_names_collected
                if isinstance(collected_names, str):
                    for fn in collected_names.split(","):
                        fn = fn.strip()
                        if fn:
                            file_names_set.add(fn)
            elif isinstance(event, DownloadedStatus):
                file_names_set.add(event.file_name_downloaded)
            elif isinstance(event, FailedStatus):
                file_names_set.add(event.file_name)

        for vd in self.verified_downloads:
            file_names_set.add(vd.file_name)

        # Build per-file event records and count status types per file
        per_file = defaultdict(
            lambda: {
                "collected": False,
                "downloaded": False,
                "failed": False,
                "verified": False,
            }
        )
        per_file_status_counter = defaultdict(list)  # List of status "types" per file

        for event in self.events:
            if isinstance(event, CollectedStatus):
                collected_names = event.file_names_collected
                if isinstance(collected_names, str):
                    for fn in collected_names.split(","):
                        fn = fn.strip()
                        if fn:
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

        # Now, for each file, validate its story and ensure no duplicate status for file
        for fn, status in per_file.items():
            # Must be collected
            if not status["collected"]:
                return False
            # Must be either downloaded OR failed
            if not (status["downloaded"] or status["failed"]):
                return False
            # If downloaded, must be also verified
            if status["downloaded"] and not status["verified"]:
                return False
            # Check duplicate statuses for the same file
            status_counter = Counter(per_file_status_counter[fn])
            for _stat_name, count in status_counter.items():
                if count > 1:
                    return False  # Duplicate status type for a file, not allowed

        return True
