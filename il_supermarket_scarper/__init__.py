from .main import ScarpingTask
from .scrappers_factory import ScraperFactory
from .scraper_stability import ScraperStability
from .utils import (
    FileTypesFilters,
    DumpFolderNames,
    datetime_in_tlv,
    ScraperStatusOutput,
    FileName,
    StartedStatus,
    FolderSizeInfo,
    EstimatedSizeStatus,
    CollectedStatus,
    DownloadedStatus,
    SawStatus,
    FailedStatus,
    VerifiedDownload,
)

# Customers import ScraperStability from here and call
# ScraperStability.is_validate_scraper_found_no_files themselves when a scrape
# returns no files. The factory does not do that check.
__all__ = [
    "ScarpingTask",
    "ScraperFactory",
    "ScraperStability",
    "FileTypesFilters",
    "DumpFolderNames",
    "datetime_in_tlv",
    "ScraperStatusOutput",
    "FileName",
    "StartedStatus",
    "FolderSizeInfo",
    "EstimatedSizeStatus",
    "CollectedStatus",
    "DownloadedStatus",
    "SawStatus",
    "FailedStatus",
    "VerifiedDownload",
]
