"""Data classes defining the output format contract for scraper status."""

from datetime import datetime
from re import S
from typing import List, Optional, Any, Dict, Union
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
    suppress_exception: bool = False


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
    status: str = "fail"
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
    global_status: List[Union[StartedStatus,EstimatedSizeStatus]] = Field(default_factory=list)
    events: List[Union[CollectedStatus,DownloadedStatus,FailedStatus]] = Field(default_factory=list)
    verified_downloads: List[VerifiedDownload] = Field(default_factory=list)
    
    
    