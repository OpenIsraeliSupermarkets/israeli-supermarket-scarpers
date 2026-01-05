"""Data classes defining the output format contract for scraper status."""

from datetime import datetime
from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field


class FolderSizeInfo(BaseModel):
    """Information about the size and contents of a folder."""
    size: float
    unit: str
    folder: str
    folder_content: List[str] = Field(default_factory=list)


class DownloadResult(BaseModel):
    """Result of a file download operation."""
    file_name: str
    downloaded: bool
    extract_succefully: bool
    error: Optional[str]
    restart_and_retry: bool


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
    suppress_exception: bool = False


class CollectedStatus(BaseModel):
    """Status event when file details are collected."""
    status: str = "collected"
    when: Optional[datetime] = None
    file_name_collected_from_site: Union[str, List[str]] = Field(default_factory=list)
    links_collected_from_site: Union[str, List[str]] = Field(default_factory=list)


class DownloadedStatus(BaseModel):
    """Status event when files are downloaded."""
    status: str = "downloaded"
    when: Optional[datetime] = None
    results: Union[DownloadResult, List[DownloadResult], Dict[str, Any]] = Field(default_factory=list)


class FailedStatus(BaseModel):
    """Status event when scraping fails."""
    status: str = "fail"
    when: Optional[datetime] = None
    execption: str = ""
    traceback: str = ""
    download_urls: List[str] = Field(default_factory=list)
    file_names: List[str] = Field(default_factory=list)


class EstimatedSizeStatus(BaseModel):
    """Status event when scraping is completed."""
    status: str = "estimated_size"
    when: Optional[datetime] = None
    folder_size: Optional[FolderSizeInfo] = None
    completed_successfully: bool = True


class VerifiedDownload(BaseModel):
    """Record of a verified downloaded file."""
    file_name: str
    when: datetime


# Union type for all possible status events
StatusEvent = Union[
    StartedStatus,
    CollectedStatus,
    DownloadedStatus,
    FailedStatus,
    EstimatedSizeStatus,
]


class ScraperStatusOutput(BaseModel):
    """
    Complete output format for scraper status.
    
    The main structure is a dictionary where:
    - Keys are task IDs (timestamp strings in format YYYYMMDDHHMMSS)
    - Values are lists of status events
    - Special key "verified_downloads" contains the list of verified downloads
    """
    tasks: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    verified_downloads: List[VerifiedDownload] = Field(default_factory=list)